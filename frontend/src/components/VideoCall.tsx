import { useEffect, useRef, useState } from 'react';
import { XCircle, Video, VideoOff, Mic, MicOff, PhoneOff, Users } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface VideoCallProps {
  meetingId: number;
  meetingTitle: string;
  onClose: () => void;
}

interface PeerConnection {
  peerId: string;
  connection: RTCPeerConnection;
  stream?: MediaStream;
}

export default function VideoCall({ meetingId, meetingTitle, onClose }: VideoCallProps) {
  const { user } = useAuthStore();
  const [roomId, setRoomId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [remoteStreams, setRemoteStreams] = useState<Map<string, MediaStream>>(new Map());
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [participants, setParticipants] = useState<any[]>([]);
  const [micPermissionDenied, setMicPermissionDenied] = useState(false);
  const [cameraPermissionDenied, setCameraPermissionDenied] = useState(false);
  const [isRequestingPermissions, setIsRequestingPermissions] = useState(true);
  const [micDeviceAvailable, setMicDeviceAvailable] = useState<boolean | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const peersRef = useRef<Map<string, RTCPeerConnection>>(new Map());
  const localStreamRef = useRef<MediaStream | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // STUN/TURN servers for WebRTC
  const rtcConfiguration: RTCConfiguration = {
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      // Add TURN servers in production for better connectivity
      // { urls: 'turn:your-turn-server.com', username: 'user', credential: 'pass' }
    ],
  };

  useEffect(() => {
    initializeCall();
    checkDeviceAvailability();
    return () => {
      cleanup();
    };
  }, []);

  const checkDeviceAvailability = async () => {
    try {
      // Check for microphone devices
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter(device => device.kind === 'audioinput');
        
        if (audioInputs.length > 0) {
          setMicDeviceAvailable(true);
          console.log('Microphone devices detected:', audioInputs.length);
        } else {
          // No devices found in enumeration
          // This might mean:
          // 1. No physical devices
          // 2. Permission not granted (devices exist but not enumerated)
          // Set to null (unknown) rather than false
          setMicDeviceAvailable(null);
        }
      } else {
        setMicDeviceAvailable(null);
      }
    } catch (error) {
      console.warn('Could not check device availability:', error);
      setMicDeviceAvailable(null); // Unknown status
    }
  };

  const refreshDeviceList = async () => {
    toast.info('Refreshing device list and checking microphone...', { duration: 2000 });
    
    // First, try to request permission and get a stream
    try {
      const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const hasAudio = testStream.getAudioTracks().length > 0;
      
      if (hasAudio) {
        // We got a stream! Use it
        const audioTracks = testStream.getAudioTracks();
        
        // Stop any existing tracks
        if (localStreamRef.current) {
          localStreamRef.current.getAudioTracks().forEach(track => {
            track.stop();
            peersRef.current.forEach((peerConnection) => {
              const sender = peerConnection.getSenders().find((s) => s.track === track);
              if (sender) {
                peerConnection.removeTrack(sender);
              }
            });
          });
        }
        
        // Add new tracks
        if (localStreamRef.current) {
          audioTracks.forEach(track => {
            localStreamRef.current!.addTrack(track);
          });
        } else {
          localStreamRef.current = testStream;
        }
        
        const newStream = new MediaStream(localStreamRef.current.getTracks());
        setLocalStream(newStream);
        setAudioEnabled(true);
        setMicPermissionDenied(false);
        setMicDeviceAvailable(true);
        
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = newStream;
        }
        
        // Update peer connections
        if (peersRef.current.size > 0) {
          peersRef.current.forEach((peerConnection, peerId) => {
            audioTracks.forEach((track) => {
              const existingSender = peerConnection.getSenders().find((s) => 
                s.track && s.track.kind === 'audio'
              );
              if (existingSender) {
                existingSender.replaceTrack(track).catch(() => {
                  peerConnection.addTrack(track, localStreamRef.current!);
                });
              } else {
                peerConnection.addTrack(track, localStreamRef.current!);
              }
            });
            
            peerConnection.createOffer()
              .then((offer) => peerConnection.setLocalDescription(offer))
              .then(() => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                  wsRef.current.send(
                    JSON.stringify({
                      type: 'offer',
                      offer: peerConnection.localDescription,
                      to: peerId,
                    })
                  );
                }
              });
          });
        }
        
        setIsRequestingPermissions(false);
        toast.success('Microphone detected and enabled!', {
          duration: 3000,
        });
      } else {
        // Stream but no audio tracks
        testStream.getTracks().forEach(track => track.stop());
        setMicDeviceAvailable(false);
        toast.error('Microphone device found but no audio tracks available.', {
          duration: 4000,
        });
      }
    } catch (error: any) {
      console.log('Could not access microphone:', error);
      
      // Update device availability based on error
      await checkDeviceAvailability();
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        setMicPermissionDenied(true);
        toast.error('Microphone permission denied. Please allow access in browser settings.', {
          duration: 5000,
        });
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        setMicDeviceAvailable(false);
        toast.error('No microphone device found. Please connect a microphone and try again.', {
          duration: 5000,
        });
      } else {
        setMicDeviceAvailable(null);
        toast.error('Could not access microphone. Please check your device and try again.', {
          duration: 5000,
        });
      }
    }
  };

  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  const initializeCall = async () => {
    try {
      // Get room info from backend
      const response = await api.get(`/api/webrtc/room/${meetingId}/info`);
      const roomId = response.data.room_id;
      setRoomId(roomId);

      // Try to get user media (camera and microphone) - but don't fail if it doesn't work
      // Users can join without media and enable it later
      try {
        await startLocalStream();
      } catch (mediaError: any) {
        console.warn('Media access failed, but continuing:', mediaError);
        // Don't block the call - user can join without media
        setIsRequestingPermissions(false);
      }

      // Connect to WebSocket signaling server (even if permissions not granted yet)
      // User can grant permissions later and we'll update the stream
      try {
        await connectWebSocket(roomId);
      } catch (wsError: any) {
        console.error('WebSocket connection failed:', wsError);
        toast.error('Failed to connect to call server. Please try again.');
        // Don't close immediately - let user see the error and retry
        setTimeout(() => {
          if (!isConnected) {
            toast.info('Retrying connection...');
            connectWebSocket(roomId).catch(() => {
              toast.error('Unable to connect. Please check your internet connection.');
            });
          }
        }, 3000);
      }
    } catch (error: any) {
      console.error('Failed to initialize call:', error);
      
      // Only show error and close if it's a critical error (room info failed)
      if (error.response?.status === 404) {
        toast.error('Meeting not found');
        onClose();
      } else if (error.response?.status === 403) {
        toast.error('You do not have permission to join this meeting');
        onClose();
      } else {
        // For other errors, try to continue anyway
        toast.warning('Some features may not be available, but you can still try to join.');
        // Try to connect WebSocket anyway if we have a roomId
        if (roomId) {
          connectWebSocket(roomId).catch(() => {
            toast.error('Connection failed. Please refresh and try again.');
          });
        }
      }
    }
  };

  const startLocalStream = async () => {
    setIsRequestingPermissions(true);
    
    // First, try to get microphone (most important for calls)
    let audioStream: MediaStream | null = null;
    let videoStream: MediaStream | null = null;
    
    try {
      // Request microphone first (critical for calls)
      audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      setMicPermissionDenied(false);
      console.log('Microphone access granted');
    } catch (audioError: any) {
      console.error('Microphone access error:', audioError);
      setMicPermissionDenied(true);
      
      if (audioError.name === 'NotAllowedError') {
        toast.info('Microphone access denied. You can still join to listen/watch others.', {
          duration: 4000,
        });
      } else if (audioError.name === 'NotFoundError') {
        toast.info('No microphone detected. You can still join to listen/watch others. Enable microphone later if needed.', {
          duration: 4000,
        });
      } else {
        toast.info('Could not access microphone. You can still join to listen/watch others.', {
          duration: 4000,
        });
      }
    }
    
    // Then try to get camera (optional)
    try {
      videoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
      });
      setCameraPermissionDenied(false);
      console.log('Camera access granted');
    } catch (videoError: any) {
      console.error('Camera access error:', videoError);
      setCameraPermissionDenied(true);
      setVideoEnabled(false);
      
      if (videoError.name === 'NotAllowedError') {
        toast.error('Camera access denied. You can still join with audio only.', {
          duration: 4000,
        });
      } else if (videoError.name === 'NotFoundError') {
        toast.info('No camera found. Joining with audio only.', {
          duration: 3000,
        });
      } else {
        toast.info('Could not access camera. Joining with audio only.', {
          duration: 3000,
        });
      }
    }
    
    // Combine streams if available, or create empty stream if none available
    // Users can join without microphone/camera - they'll just be viewers/listeners
    if (audioStream || videoStream) {
      const combinedStream = new MediaStream();
      
      if (audioStream) {
        audioStream.getAudioTracks().forEach(track => combinedStream.addTrack(track));
      }
      
      if (videoStream) {
        videoStream.getVideoTracks().forEach(track => combinedStream.addTrack(track));
      }
      
      localStreamRef.current = combinedStream;
      setLocalStream(combinedStream);
      
      // Update enabled states based on what we got
      if (!audioStream) {
        setAudioEnabled(false);
      }
      if (!videoStream) {
        setVideoEnabled(false);
      }
      
      if (!audioStream && !videoStream) {
        // This shouldn't happen, but handle it
        localStreamRef.current = null;
        setLocalStream(null);
      }
    } else {
      // No media devices available - user can still join as viewer/listener
      localStreamRef.current = null;
      setLocalStream(null);
      setAudioEnabled(false);
      setVideoEnabled(false);
      
      toast.info('No microphone or camera access. You can still join to listen/watch others.', {
        duration: 4000,
      });
    }
    
    setIsRequestingPermissions(false);
  };

  const retryPermissions = async () => {
    setIsRequestingPermissions(true);
    
    // Stop existing streams
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        track.stop();
        // Remove track from all peer connections
        peersRef.current.forEach((peerConnection) => {
          const sender = peerConnection.getSenders().find((s) => s.track === track);
          if (sender) {
            peerConnection.removeTrack(sender);
          }
        });
      });
    }
    
    // Reset states
    setMicPermissionDenied(false);
    setCameraPermissionDenied(false);
    
    // Retry getting permissions
    await startLocalStream();
    
    // If we got a stream, update all peer connections
    if (localStreamRef.current && roomId && peersRef.current.size > 0) {
      // Add new tracks to all existing peer connections
      peersRef.current.forEach((peerConnection, peerId) => {
        if (localStreamRef.current) {
          localStreamRef.current.getTracks().forEach((track) => {
            // Check if track of this kind already exists
            const existingSender = peerConnection.getSenders().find((s) => 
              s.track && s.track.kind === track.kind
            );
            
            if (existingSender) {
              // Replace existing track
              existingSender.replaceTrack(track).catch((error) => {
                console.error('Error replacing track:', error);
              });
            } else {
              // Add new track
              peerConnection.addTrack(track, localStreamRef.current!);
              
              // If we're adding a track, we need to renegotiate
              // Create a new offer
              peerConnection.createOffer()
                .then((offer) => {
                  return peerConnection.setLocalDescription(offer);
                })
                .then(() => {
                  // Send offer to peer
                  wsRef.current?.send(
                    JSON.stringify({
                      type: 'offer',
                      offer: peerConnection.localDescription,
                      to: peerId,
                    })
                  );
                })
                .catch((error) => {
                  console.error('Error creating offer after adding track:', error);
                });
            }
          });
        }
      });
    }
  };

  const connectWebSocket = async (roomId: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('token');
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // Convert HTTP/HTTPS URL to WebSocket URL
      let wsUrl: string;
      if (apiUrl.startsWith('https://')) {
        wsUrl = apiUrl.replace('https://', 'wss://');
      } else if (apiUrl.startsWith('http://')) {
        wsUrl = apiUrl.replace('http://', 'ws://');
      } else {
        // Fallback: assume protocol based on current page
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${apiUrl.replace(/^https?:\/\//, '')}`;
      }
      
      const fullWsUrl = `${wsUrl}/api/webrtc/ws/${roomId}?token=${token || ''}&user_id=${user?.id}&user_name=${encodeURIComponent(user?.full_name || 'User')}`;

      try {
        const ws = new WebSocket(fullWsUrl);
        wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        resolve();
      };

      ws.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          await handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        reject(new Error('WebSocket connection error'));
        // Still schedule reconnect attempt
        scheduleReconnect(roomId);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        setIsConnected(false);
        if (event.code !== 1000 && wsRef.current) {
          // Not a normal closure - try to reconnect
          scheduleReconnect(roomId);
        }
      };
      
      // Set a timeout for connection
      setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          ws.close();
          reject(new Error('WebSocket connection timeout'));
        }
      }, 10000); // 10 second timeout
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      reject(error);
    }
    });
  };

  const scheduleReconnect = (roomId: string) => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectTimeoutRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.CLOSED) {
        connectWebSocket(roomId);
      }
    }, 3000);
  };

  const handleWebSocketMessage = async (message: any) => {
    switch (message.type) {
      case 'room_info':
        // Received room info with existing participants
        setParticipants(message.participants || []);
        // Create peer connections for existing participants
        for (const participant of message.participants) {
          if (participant.user_id !== String(user?.id)) {
            await createPeerConnection(participant.user_id, true);
          }
        }
        break;

      case 'user_joined':
        // New user joined
        setParticipants((prev) => [...prev, message.user]);
        if (message.user.user_id !== String(user?.id)) {
          await createPeerConnection(message.user.user_id, true);
        }
        toast.success(`${message.user.user_name} joined the call`);
        break;

      case 'user_left':
        // User left
        setParticipants((prev) => prev.filter((p) => p.user_id !== message.user.user_id));
        closePeerConnection(message.user.user_id);
        toast.info(`${message.user.user_name} left the call`);
        break;

      case 'offer':
        // Received offer from another peer
        await handleOffer(message.from, message.offer);
        break;

      case 'answer':
        // Received answer from another peer
        if (message.to === String(user?.id)) {
          await handleAnswer(message.from, message.answer);
        }
        break;

      case 'ice_candidate':
        // Received ICE candidate
        await handleIceCandidate(message.from, message.candidate);
        break;

      case 'user_audio_toggled':
        // User toggled audio
        toast.info(`${message.user_id} ${message.audio_enabled ? 'unmuted' : 'muted'}`);
        break;

      case 'user_video_toggled':
        // User toggled video
        toast.info(`${message.user_id} ${message.video_enabled ? 'enabled' : 'disabled'} video`);
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const createPeerConnection = async (peerId: string, isInitiator: boolean): Promise<void> => {
    if (peersRef.current.has(peerId)) {
      return; // Already connected
    }

    const peerConnection = new RTCPeerConnection(rtcConfiguration);
    peersRef.current.set(peerId, peerConnection);

    // Add local stream tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        peerConnection.addTrack(track, localStreamRef.current!);
      });
    }

    // Handle remote stream
    peerConnection.ontrack = (event) => {
      const [remoteStream] = event.streams;
      setRemoteStreams((prev) => {
        const newMap = new Map(prev);
        newMap.set(peerId, remoteStream);
        return newMap;
      });
    };

    // Handle ICE candidates
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'ice_candidate',
            candidate: event.candidate,
            to: peerId,
          })
        );
      }
    };

    // Handle connection state changes
    peerConnection.onconnectionstatechange = () => {
      console.log(`Peer ${peerId} connection state:`, peerConnection.connectionState);
      if (peerConnection.connectionState === 'failed' || peerConnection.connectionState === 'disconnected') {
        closePeerConnection(peerId);
      }
    };

    // Create and send offer if initiator
    if (isInitiator) {
      try {
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        wsRef.current?.send(
          JSON.stringify({
            type: 'offer',
            offer: offer,
            to: peerId,
          })
        );
      } catch (error) {
        console.error('Error creating offer:', error);
      }
    }
  };

  const handleOffer = async (from: string, offer: RTCSessionDescriptionInit): Promise<void> => {
    await createPeerConnection(from, false);
    const peerConnection = peersRef.current.get(from);
    if (peerConnection) {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
      const answer = await peerConnection.createAnswer();
      await peerConnection.setLocalDescription(answer);
      wsRef.current?.send(
        JSON.stringify({
          type: 'answer',
          answer: answer,
          to: from,
        })
      );
    }
  };

  const handleAnswer = async (from: string, answer: RTCSessionDescriptionInit): Promise<void> => {
    const peerConnection = peersRef.current.get(from);
    if (peerConnection) {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    }
  };

  const handleIceCandidate = async (from: string, candidate: RTCIceCandidateInit): Promise<void> => {
    const peerConnection = peersRef.current.get(from);
    if (peerConnection) {
      await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    }
  };

  const closePeerConnection = (peerId: string) => {
    const peerConnection = peersRef.current.get(peerId);
    if (peerConnection) {
      peerConnection.close();
      peersRef.current.delete(peerId);
    }
    setRemoteStreams((prev) => {
      const newMap = new Map(prev);
      newMap.delete(peerId);
      return newMap;
    });
  };

  const checkMicrophoneAvailable = async (): Promise<boolean> => {
    try {
      // Check if getUserMedia is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('getUserMedia not available');
        return false;
      }
      
      // Try to enumerate devices to check for audio input
      // Note: device labels may be empty until permission is granted
      let devices: MediaDeviceInfo[] = [];
      try {
        devices = await navigator.mediaDevices.enumerateDevices();
      } catch (enumError) {
        console.warn('Could not enumerate devices:', enumError);
        // If enumeration fails, we can't determine availability
        // But we should still try to request access
        return true; // Assume available, let getUserMedia handle it
      }
      
      const audioInputs = devices.filter(device => device.kind === 'audioinput');
      console.log('Found audio input devices:', audioInputs.length, audioInputs.map(d => ({
        deviceId: d.deviceId,
        label: d.label || 'Unknown device',
        kind: d.kind
      })));
      
      // If we have devices, return true
      if (audioInputs.length > 0) {
        return true;
      }
      
      // If no devices found but we can enumerate, might mean:
      // 1. No physical devices connected
      // 2. Permissions not granted (labels empty, but devices exist)
      // Try a quick permission request to see if devices become available
      try {
        // Request temporary access to see if devices exist
        const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const hasAudio = testStream.getAudioTracks().length > 0;
        // Stop the test stream immediately
        testStream.getTracks().forEach(track => track.stop());
        
        if (hasAudio) {
          // Devices exist, just needed permission
          return true;
        }
      } catch (testError) {
        // Permission denied or no devices - either way, we'll handle it in enableMicrophone
        console.log('Test access failed:', testError);
      }
      
      return false;
    } catch (error) {
      console.warn('Could not check microphone availability:', error);
      // If we can't check, assume it might be available and let getUserMedia handle it
      return true;
    }
  };

  const enableMicrophone = async (): Promise<boolean> => {
    try {
      // Note: We don't check availability first because:
      // 1. Device enumeration might not work until permission is granted
      // 2. Some systems have default microphones that aren't enumerated
      // 3. getUserMedia will handle the actual device detection
      
      // Try to request microphone access directly
      // The browser will handle device selection automatically

      // First try with optimal settings
      let audioStream: MediaStream;
      try {
        audioStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            // Allow browser to select the best available microphone
            sampleRate: { ideal: 48000 },
            channelCount: { ideal: 1 },
          },
        });
      } catch (constraintError: any) {
        // If optimal constraints fail, try with minimal constraints
        console.log('Optimal constraints failed, trying minimal constraints:', constraintError);
        try {
          audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (fallbackError: any) {
          // If minimal constraints also fail, rethrow to outer catch
          throw fallbackError;
        }
      }
      
      // Verify we got an audio track
      const audioTracks = audioStream.getAudioTracks();
      if (audioTracks.length === 0) {
        throw new Error('No audio tracks in stream');
      }
      
      // Log device info for debugging
      audioTracks.forEach(track => {
        const settings = track.getSettings();
        console.log('Microphone enabled:', {
          deviceId: settings.deviceId,
          label: track.label,
          enabled: track.enabled,
          readyState: track.readyState,
        });
      });
      
      // Add audio track to existing stream or create new stream
      if (localStreamRef.current) {
        // Remove existing audio tracks first
        localStreamRef.current.getAudioTracks().forEach(track => {
          track.stop();
          // Remove from peer connections
          peersRef.current.forEach((peerConnection) => {
            const sender = peerConnection.getSenders().find((s) => s.track === track);
            if (sender) {
              peerConnection.removeTrack(sender);
            }
          });
        });
        
        // Add new audio tracks
        audioTracks.forEach(track => {
          localStreamRef.current!.addTrack(track);
        });
      } else {
        localStreamRef.current = audioStream;
      }
      
      // Create new stream with all tracks
      const newStream = new MediaStream(localStreamRef.current.getTracks());
      setLocalStream(newStream);
      setAudioEnabled(true);
      setMicPermissionDenied(false);
      
      // Update video element if it exists
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = newStream;
      }
      
      // Update all peer connections
      if (peersRef.current.size > 0) {
        peersRef.current.forEach((peerConnection, peerId) => {
          audioTracks.forEach((track) => {
            // Check if audio track already exists
            const existingSender = peerConnection.getSenders().find((s) => 
              s.track && s.track.kind === 'audio'
            );
            
            if (existingSender) {
              existingSender.replaceTrack(track).catch((error) => {
                console.error('Error replacing audio track:', error);
                // If replace fails, try adding as new track
                peerConnection.addTrack(track, localStreamRef.current!);
              });
            } else {
              peerConnection.addTrack(track, localStreamRef.current!);
            }
          });
          
          // Renegotiate connection
          peerConnection.createOffer()
            .then((offer) => peerConnection.setLocalDescription(offer))
            .then(() => {
              if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(
                  JSON.stringify({
                    type: 'offer',
                    offer: peerConnection.localDescription,
                    to: peerId,
                  })
                );
              }
            })
            .catch((error) => console.error('Error creating offer:', error));
        });
      } else {
        // No peer connections yet, but stream is ready for when peers join
        console.log('Microphone enabled, ready for peer connections');
      }
      
      // Close permission overlay if it's open
      setIsRequestingPermissions(false);
      
      toast.success('Microphone enabled successfully! Device microphone is now active.', {
        duration: 3000,
      });
      return true;
    } catch (error: any) {
      console.error('Failed to get microphone:', error);
      setMicPermissionDenied(true);
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        toast.error('Microphone access denied. Please allow microphone access in your browser settings and try again.', {
          duration: 6000,
        });
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        // Try with minimal constraints before giving up
        console.log('Device not found with optimal constraints, trying minimal constraints...');
        try {
          const fallbackStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const fallbackTracks = fallbackStream.getAudioTracks();
          
          if (fallbackTracks.length > 0) {
            // Success with minimal constraints!
            if (localStreamRef.current) {
              localStreamRef.current.getAudioTracks().forEach(track => track.stop());
              fallbackTracks.forEach(track => {
                localStreamRef.current!.addTrack(track);
              });
            } else {
              localStreamRef.current = fallbackStream;
            }
            
            setLocalStream(new MediaStream(localStreamRef.current.getTracks()));
            setAudioEnabled(true);
            setMicPermissionDenied(false);
            setMicDeviceAvailable(true);
            
            if (localVideoRef.current) {
              localVideoRef.current.srcObject = localStreamRef.current;
            }
            
            // Update peer connections
            if (peersRef.current.size > 0) {
              peersRef.current.forEach((peerConnection, peerId) => {
                fallbackTracks.forEach((track) => {
                  const existingSender = peerConnection.getSenders().find((s) => 
                    s.track && s.track.kind === 'audio'
                  );
                  if (existingSender) {
                    existingSender.replaceTrack(track).catch(() => {
                      peerConnection.addTrack(track, localStreamRef.current!);
                    });
                  } else {
                    peerConnection.addTrack(track, localStreamRef.current!);
                  }
                });
                
                peerConnection.createOffer()
                  .then((offer) => peerConnection.setLocalDescription(offer))
                  .then(() => {
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                      wsRef.current.send(
                        JSON.stringify({
                          type: 'offer',
                          offer: peerConnection.localDescription,
                          to: peerId,
                        })
                      );
                    }
                  });
              });
            }
            
            setIsRequestingPermissions(false);
            toast.success('Microphone enabled successfully!', {
              duration: 3000,
            });
            return true;
          }
        } catch (fallbackError: any) {
          // Even minimal constraints failed
          console.error('Fallback also failed:', fallbackError);
          setMicDeviceAvailable(false);
          toast.error(
            'No microphone device found. Please check: 1) Microphone is connected, 2) Enabled in system settings, 3) Not used by another app. Click Refresh to check again.',
            {
              duration: 8000,
            }
          );
        }
      } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        toast.error('Microphone is being used by another application. Please close other apps using the microphone.', {
          duration: 6000,
        });
      } else if (error.name === 'OverconstrainedError') {
        toast.info('Microphone constraints could not be satisfied. Trying with default settings...', {
          duration: 4000,
        });
        // Retry with simpler constraints
        try {
          const fallbackStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const fallbackTracks = fallbackStream.getAudioTracks();
          
          if (fallbackTracks.length > 0) {
            // Use the fallback stream
            if (localStreamRef.current) {
              localStreamRef.current.getAudioTracks().forEach(track => track.stop());
              fallbackTracks.forEach(track => {
                localStreamRef.current!.addTrack(track);
              });
            } else {
              localStreamRef.current = fallbackStream;
            }
            
            setLocalStream(new MediaStream(localStreamRef.current.getTracks()));
            setAudioEnabled(true);
            setMicPermissionDenied(false);
            
            // Update peer connections
            if (peersRef.current.size > 0) {
              peersRef.current.forEach((peerConnection, peerId) => {
                fallbackTracks.forEach((track) => {
                  const existingSender = peerConnection.getSenders().find((s) => 
                    s.track && s.track.kind === 'audio'
                  );
                  if (existingSender) {
                    existingSender.replaceTrack(track);
                  } else {
                    peerConnection.addTrack(track, localStreamRef.current!);
                  }
                });
                
                peerConnection.createOffer()
                  .then((offer) => peerConnection.setLocalDescription(offer))
                  .then(() => {
                    if (wsRef.current?.readyState === WebSocket.OPEN) {
                      wsRef.current.send(
                        JSON.stringify({
                          type: 'offer',
                          offer: peerConnection.localDescription,
                          to: peerId,
                        })
                      );
                    }
                  });
              });
            }
            
            toast.success('Microphone enabled with default settings!');
            return true;
          }
        } catch (fallbackError: any) {
          toast.error('Could not access microphone with any settings.', {
            duration: 5000,
          });
          return false;
        }
      } else {
        toast.error(`Could not access microphone: ${error.message || 'Unknown error'}. Please check your browser permissions and device connections.`, {
          duration: 6000,
        });
      }
      return false;
    }
  };

  const enableCamera = async (): Promise<boolean> => {
    try {
      const videoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
      });
      
      // Add video track to existing stream or create new stream
      if (localStreamRef.current) {
        // Remove existing video tracks first
        localStreamRef.current.getVideoTracks().forEach(track => track.stop());
        videoStream.getVideoTracks().forEach(track => {
          localStreamRef.current!.addTrack(track);
        });
      } else {
        localStreamRef.current = videoStream;
      }
      
      setLocalStream(new MediaStream(localStreamRef.current.getTracks()));
      setVideoEnabled(true);
      setCameraPermissionDenied(false);
      
      // Update video element if it exists
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = localStreamRef.current;
      }
      
      // Update all peer connections
      if (peersRef.current.size > 0) {
        peersRef.current.forEach((peerConnection, peerId) => {
          videoStream.getVideoTracks().forEach((track) => {
            const existingSender = peerConnection.getSenders().find((s) => 
              s.track && s.track.kind === 'video'
            );
            
            if (existingSender) {
              existingSender.replaceTrack(track).catch((error) => {
                console.error('Error replacing video track:', error);
              });
            } else {
              peerConnection.addTrack(track, localStreamRef.current!);
            }
          });
          
          // Renegotiate connection
          peerConnection.createOffer()
            .then((offer) => peerConnection.setLocalDescription(offer))
            .then(() => {
              wsRef.current?.send(
                JSON.stringify({
                  type: 'offer',
                  offer: peerConnection.localDescription,
                  to: peerId,
                })
              );
            })
            .catch((error) => console.error('Error creating offer:', error));
        });
      }
      
      // Close permission overlay if it's open
      setIsRequestingPermissions(false);
      
      toast.success('Camera enabled successfully!');
      return true;
    } catch (error: any) {
      console.error('Failed to get camera:', error);
      setCameraPermissionDenied(true);
      if (error.name === 'NotAllowedError') {
        toast.error('Camera access denied. Please allow camera access in your browser settings.', {
          duration: 5000,
        });
      } else if (error.name === 'NotFoundError') {
        toast.error('No camera detected. Please connect a camera device.', {
          duration: 5000,
        });
      } else {
        toast.error('Could not access camera. Please check your browser permissions.', {
          duration: 5000,
        });
      }
      return false;
    }
  };

  const grantAllPermissions = async () => {
    setIsRequestingPermissions(true);
    toast.info('Requesting microphone and camera permissions...', {
      duration: 3000,
    });
    
    try {
      // Request both permissions simultaneously
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
      });
      
      // Successfully got both permissions
      const audioTracks = stream.getAudioTracks();
      const videoTracks = stream.getVideoTracks();
      
      // Stop any existing tracks
      if (localStreamRef.current) {
        localStreamRef.current.getTracks().forEach(track => {
          track.stop();
          peersRef.current.forEach((peerConnection) => {
            const sender = peerConnection.getSenders().find((s) => s.track === track);
            if (sender) {
              peerConnection.removeTrack(sender);
            }
          });
        });
      }
      
      // Create new stream with all tracks
      localStreamRef.current = stream;
      setLocalStream(new MediaStream(stream.getTracks()));
      setAudioEnabled(audioTracks.length > 0);
      setVideoEnabled(videoTracks.length > 0);
      setMicPermissionDenied(false);
      setCameraPermissionDenied(false);
      
      // Update video element
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      
      // Update all peer connections
      if (peersRef.current.size > 0 && roomId) {
        peersRef.current.forEach((peerConnection, peerId) => {
          stream.getTracks().forEach((track) => {
            const existingSender = peerConnection.getSenders().find((s) => 
              s.track && s.track.kind === track.kind
            );
            
            if (existingSender) {
              existingSender.replaceTrack(track).catch((error) => {
                console.error('Error replacing track:', error);
              });
            } else {
              peerConnection.addTrack(track, stream);
            }
          });
          
          // Renegotiate connection
          peerConnection.createOffer()
            .then((offer) => peerConnection.setLocalDescription(offer))
            .then(() => {
              if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(
                  JSON.stringify({
                    type: 'offer',
                    offer: peerConnection.localDescription,
                    to: peerId,
                  })
                );
              }
            })
            .catch((error) => console.error('Error creating offer:', error));
        });
      }
      
      setIsRequestingPermissions(false);
      toast.success('All permissions granted! Microphone and camera are now enabled.', {
        duration: 4000,
      });
    } catch (error: any) {
      console.error('Failed to get permissions:', error);
      
      // Try to get permissions individually
      const micSuccess = await enableMicrophone();
      const cameraSuccess = await enableCamera();
      
      setIsRequestingPermissions(false);
      
      if (micSuccess && cameraSuccess) {
        toast.success('All permissions granted! Microphone and camera are now enabled.', {
          duration: 4000,
        });
      } else if (micSuccess || cameraSuccess) {
        toast.info('Some permissions were granted. You can enable the rest later.', {
          duration: 4000,
        });
      } else {
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          toast.error('Permissions were denied. Please allow access in your browser settings.', {
            duration: 5000,
          });
        } else {
          toast.error('Could not access media devices. Please check your browser permissions.', {
            duration: 5000,
          });
        }
      }
    }
  };

  const toggleAudio = async () => {
    if (localStreamRef.current) {
      const audioTracks = localStreamRef.current.getAudioTracks();
      if (audioTracks.length > 0 && audioTracks[0].enabled !== undefined) {
        // Toggle existing audio track
        const newState = !audioEnabled;
        audioTracks.forEach((track) => {
          track.enabled = newState;
        });
        setAudioEnabled(newState);
        wsRef.current?.send(
          JSON.stringify({
            type: 'toggle_audio',
            audio_enabled: newState,
          })
        );
      } else {
        // No audio track - enable microphone
        await enableMicrophone();
      }
    } else {
      // No stream at all - enable microphone
      await enableMicrophone();
    }
  };

  const toggleVideo = async () => {
    if (localStreamRef.current) {
      const videoTracks = localStreamRef.current.getVideoTracks();
      if (videoTracks.length > 0 && videoTracks[0].enabled !== undefined) {
        // Toggle existing video track
        const newState = !videoEnabled;
        videoTracks.forEach((track) => {
          track.enabled = newState;
        });
        setVideoEnabled(newState);
        wsRef.current?.send(
          JSON.stringify({
            type: 'toggle_video',
            video_enabled: newState,
          })
        );
      } else {
        // No video track - enable camera
        await enableCamera();
      }
    } else {
      // No stream at all - enable camera
      await enableCamera();
    }
  };

  const leaveCall = () => {
    cleanup();
    onClose();
  };

  const cleanup = () => {
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Close all peer connections
    peersRef.current.forEach((peerConnection) => {
      peerConnection.close();
    });
    peersRef.current.clear();

    // Stop local stream
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        track.stop();
      });
      localStreamRef.current = null;
    }

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-95 flex flex-col z-50">
      {/* Header */}
      <div className="bg-gray-900 text-white p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold">{meetingTitle}</h2>
          <div className="flex items-center gap-2 text-sm">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Users size={16} />
            <span>{participants.length + 1} participant{participants.length !== 0 ? 's' : ''}</span>
          </div>
          {(!localStream || localStream.getAudioTracks().length === 0) && (
            <div className="flex items-center gap-2 text-sm text-blue-400">
              <MicOff size={16} />
              <span>Listening mode</span>
              {micDeviceAvailable === false && (
                <span className="text-yellow-400 text-xs" title="No microphone device detected. Connect a microphone to enable audio.">
                  (No mic device)
                </span>
              )}
              {micDeviceAvailable === null && (
                <span className="text-gray-400 text-xs" title="Microphone status unknown. Click microphone button to check.">
                  (Unknown)
                </span>
              )}
            </div>
          )}
          {localStream && localStream.getAudioTracks().length > 0 && (
            <div className="flex items-center gap-2 text-sm text-green-400">
              <Mic size={16} />
              <span>Microphone active</span>
            </div>
          )}
        </div>
        <button
          onClick={leaveCall}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <XCircle size={24} />
        </button>
      </div>

      {/* Permission Request Overlay */}
      {isRequestingPermissions && (
        <div className="absolute inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-8 max-w-md text-center">
            <div className="mb-4">
              <Mic size={48} className="mx-auto text-blue-400 mb-4 animate-pulse" />
              <h3 className="text-xl font-bold text-white mb-2">Requesting Media Access</h3>
              <p className="text-gray-300 mb-4">
                Please allow microphone and camera access if you want to participate. You can also join without them to listen/watch.
              </p>
            </div>
            <div className="text-sm text-gray-400 mb-4">
              Click "Allow" when prompted by your browser, or click "Grant All Permissions" to request again.
            </div>
            <div className="flex flex-col gap-3">
              <button
                onClick={async () => {
                  await grantAllPermissions();
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors w-full"
              >
                Grant All Permissions
              </button>
              <div className="flex gap-3">
                <button
                  onClick={async () => {
                    await enableMicrophone();
                  }}
                  className="bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 px-4 rounded-lg transition-colors flex-1"
                >
                  Enable Microphone Only
                </button>
                <button
                  onClick={async () => {
                    await enableCamera();
                  }}
                  className="bg-gray-700 hover:bg-gray-600 text-white font-medium py-3 px-4 rounded-lg transition-colors flex-1"
                >
                  Enable Camera Only
                </button>
              </div>
              <button
                onClick={() => {
                  setIsRequestingPermissions(false);
                  toast.info('Joining call without microphone/camera. You can enable them later.');
                }}
                className="bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors w-full text-sm"
              >
                Skip & Join Without Media
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Microphone Permission Denied Banner - Non-blocking */}
      {micPermissionDenied && !isRequestingPermissions && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg z-40 flex items-center gap-3 max-w-2xl">
          <MicOff size={20} />
          <div className="flex-1">
            {micDeviceAvailable === false ? (
              <span>No microphone device found. Please connect a microphone.</span>
            ) : (
              <span>Microphone not available. Click to enable microphone access.</span>
            )}
          </div>
          <div className="flex gap-2">
            {micDeviceAvailable === false && (
              <button
                onClick={refreshDeviceList}
                className="bg-blue-700 hover:bg-blue-800 px-3 py-1 rounded text-sm font-medium whitespace-nowrap"
                title="Refresh device list"
              >
                Refresh
              </button>
            )}
            <button
              onClick={enableMicrophone}
              className="bg-blue-700 hover:bg-blue-800 px-4 py-1 rounded text-sm font-medium whitespace-nowrap"
            >
              Enable Microphone
            </button>
          </div>
        </div>
      )}

      {/* Grant All Permissions Banner */}
      {(!localStream || (localStream.getAudioTracks().length === 0 && localStream.getVideoTracks().length === 0)) && !isRequestingPermissions && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-40 flex items-center gap-3 max-w-2xl">
          <Video size={20} />
          <span>Enable microphone and camera to participate in the call.</span>
          <button
            onClick={grantAllPermissions}
            className="bg-green-700 hover:bg-green-800 px-4 py-1 rounded text-sm font-medium whitespace-nowrap"
          >
            Grant All Permissions
          </button>
        </div>
      )}

      {/* Video Grid */}
      <div className="flex-1 p-4 overflow-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-7xl mx-auto">
          {/* Local Video */}
          <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-video">
            {localStream && localStream.getVideoTracks().length > 0 ? (
              <video
                ref={localVideoRef}
                autoPlay
                muted
                playsInline
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
                <div className="text-center">
                  {localStream && localStream.getAudioTracks().length > 0 ? (
                    <>
                      <Mic size={64} className="text-gray-400 mx-auto mb-2" />
                      <p className="text-gray-400 text-sm">Audio Only</p>
                    </>
                  ) : (
                    <>
                      <VideoOff size={64} className="text-gray-600 mx-auto mb-2" />
                      <p className="text-gray-400 text-sm">No Media</p>
                    </>
                  )}
                </div>
              </div>
            )}
            <div className="absolute bottom-2 left-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-sm">
              {user?.full_name || 'You'} 
              {!localStream || localStream.getVideoTracks().length === 0 ? ' (No Video)' : videoEnabled ? '' : ' (Video Off)'}
              {!localStream || localStream.getAudioTracks().length === 0 ? ' (No Audio)' : audioEnabled ? '' : ' (Muted)'}
            </div>
          </div>

          {/* Remote Videos */}
          {Array.from(remoteStreams.entries()).map(([peerId, stream]) => {
            const participant = participants.find((p) => p.user_id === peerId);
            return (
              <RemoteVideo
                key={peerId}
                stream={stream}
                peerId={peerId}
                participantName={participant?.user_name || 'Participant'}
              />
            );
          })}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-gray-900 p-4 flex items-center justify-center gap-4">
        <button
          onClick={toggleAudio}
          className={`p-4 rounded-full transition-colors ${
            audioEnabled && !micPermissionDenied
              ? 'bg-gray-700 hover:bg-gray-600 text-white'
              : 'bg-red-600 hover:bg-red-700 text-white'
          }`}
          title={
            micPermissionDenied
              ? 'Grant microphone access'
              : audioEnabled
              ? 'Mute'
              : 'Unmute'
          }
        >
          {audioEnabled && !micPermissionDenied ? <Mic size={24} /> : <MicOff size={24} />}
        </button>

        <button
          onClick={toggleVideo}
          className={`p-4 rounded-full transition-colors ${
            videoEnabled
              ? 'bg-gray-700 hover:bg-gray-600 text-white'
              : 'bg-red-600 hover:bg-red-700 text-white'
          }`}
          title={videoEnabled ? 'Turn off camera' : 'Turn on camera'}
        >
          {videoEnabled ? <Video size={24} /> : <VideoOff size={24} />}
        </button>

        <button
          onClick={leaveCall}
          className="p-4 rounded-full bg-red-600 hover:bg-red-700 text-white transition-colors"
          title="Leave call"
        >
          <PhoneOff size={24} />
        </button>
      </div>
    </div>
  );
}

function RemoteVideo({
  stream,
  peerId,
  participantName,
}: {
  stream: MediaStream;
  peerId: string;
  participantName: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoEnabled, setVideoEnabled] = useState(true);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      // Check if video track is enabled
      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        setVideoEnabled(videoTrack.enabled);
        videoTrack.onended = () => setVideoEnabled(false);
      }
    }
  }, [stream]);

  return (
    <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-video">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full h-full object-cover"
      />
      <div className="absolute bottom-2 left-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-sm">
        {participantName} {videoEnabled ? '' : '(Video Off)'}
      </div>
      {!videoEnabled && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <VideoOff size={64} className="text-gray-600" />
        </div>
      )}
    </div>
  );
}

