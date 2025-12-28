from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, List, Set, Optional
import json
import uuid
from datetime import datetime
from database import get_db, SessionLocal
from sqlalchemy.orm import Session
from models import Meeting, User, ProjectMember
from auth import get_current_active_user_ws, get_current_active_user

router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])

# Store active rooms and their participants
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}  # room_id -> set of websockets
        self.user_rooms: Dict[WebSocket, str] = {}  # websocket -> room_id
        self.user_info: Dict[WebSocket, dict] = {}  # websocket -> user info
    
    def join_room(self, room_id: str, websocket: WebSocket, user_info: dict):
        """Add a user to a room."""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        
        self.rooms[room_id].add(websocket)
        self.user_rooms[websocket] = room_id
        self.user_info[websocket] = user_info
        
        return len(self.rooms[room_id])
    
    def leave_room(self, websocket: WebSocket):
        """Remove a user from a room."""
        room_id = self.user_rooms.get(websocket)
        if room_id and room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if len(self.rooms[room_id]) == 0:
                del self.rooms[room_id]
        
        self.user_rooms.pop(websocket, None)
        self.user_info.pop(websocket, None)
    
    def get_room_participants(self, room_id: str) -> List[dict]:
        """Get list of participants in a room."""
        if room_id not in self.rooms:
            return []
        
        return [self.user_info[ws] for ws in self.rooms[room_id] if ws in self.user_info]
    
    def broadcast_to_room(self, room_id: str, message: dict, exclude: WebSocket = None):
        """Broadcast a message to all participants in a room."""
        if room_id not in self.rooms:
            return
        
        disconnected = set()
        for ws in self.rooms[room_id]:
            if ws != exclude:
                try:
                    ws.send_json(message)
                except Exception:
                    disconnected.add(ws)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.leave_room(ws)

# Global room manager instance
room_manager = RoomManager()


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for WebRTC signaling."""
    await websocket.accept()
    
    try:
        # Get token from query params
        token = websocket.query_params.get("token")
        db = SessionLocal()
        user = None
        
        if token:
            user = await get_current_active_user_ws(token, db)
        
        if not user:
            # Fallback to query params if token not available (for development)
            user_id = websocket.query_params.get("user_id")
            user_name = websocket.query_params.get("user_name", "Anonymous")
            if not user_id:
                await websocket.close(code=1008, reason="Authentication required")
                db.close()
                return
        else:
            user_id = str(user.id)
            user_name = user.full_name
        
        user_info = {
            "user_id": user_id,
            "user_name": user_name,
            "joined_at": datetime.utcnow().isoformat()
        }
        
        # Join the room
        participant_count = room_manager.join_room(room_id, websocket, user_info)
        
        if db:
            db.close()
        
        # Notify others that a new user joined
        room_manager.broadcast_to_room(
            room_id,
            {
                "type": "user_joined",
                "user": user_info,
                "participant_count": participant_count
            },
            exclude=websocket
        )
        
        # Send list of existing participants to the new user
        existing_participants = room_manager.get_room_participants(room_id)
        await websocket.send_json({
            "type": "room_info",
            "room_id": room_id,
            "participants": existing_participants,
            "your_id": user_id
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "offer":
                    # Forward offer to other participants
                    room_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "offer",
                            "offer": message.get("offer"),
                            "from": user_id,
                            "from_name": user_name
                        },
                        exclude=websocket
                    )
                
                elif message_type == "answer":
                    # Forward answer to the specific peer
                    room_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "answer",
                            "answer": message.get("answer"),
                            "from": user_id,
                            "from_name": user_name,
                            "to": message.get("to")
                        },
                        exclude=websocket
                    )
                
                elif message_type == "ice_candidate":
                    # Forward ICE candidate to other participants
                    room_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "ice_candidate",
                            "candidate": message.get("candidate"),
                            "from": user_id,
                            "from_name": user_name
                        },
                        exclude=websocket
                    )
                
                elif message_type == "toggle_audio":
                    # Broadcast audio toggle
                    room_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "user_audio_toggled",
                            "user_id": user_id,
                            "audio_enabled": message.get("audio_enabled", False)
                        },
                        exclude=websocket
                    )
                
                elif message_type == "toggle_video":
                    # Broadcast video toggle
                    room_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "user_video_toggled",
                            "user_id": user_id,
                            "video_enabled": message.get("video_enabled", False)
                        },
                        exclude=websocket
                    )
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
    
    except WebSocketDisconnect:
        # User disconnected
        room_id = room_manager.user_rooms.get(websocket)
        user_info = room_manager.user_info.get(websocket, {})
        
        room_manager.leave_room(websocket)
        
        if room_id:
            # Notify others that user left
            room_manager.broadcast_to_room(
                room_id,
                {
                    "type": "user_left",
                    "user": user_info,
                    "participant_count": len(room_manager.rooms.get(room_id, set()))
                }
            )
    except Exception as e:
        print(f"WebSocket error: {e}")
        room_manager.leave_room(websocket)


@router.get("/room/{meeting_id}/info")
async def get_room_info(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get meeting room information and verify access."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check if user has access to this meeting's project
    if current_user.role.value not in ["professor", "admin"]:
        member = db.query(ProjectMember).filter(
            ProjectMember.project_id == meeting.project_id,
            ProjectMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized to access this meeting")
    
    # Generate or use existing room ID
    if not meeting.meeting_room_url:
        # Generate a room ID based on meeting ID
        room_id = f"meeting_{meeting.id}_{uuid.uuid4().hex[:8]}"
        meeting.meeting_room_url = room_id
        db.commit()
        db.refresh(meeting)
    else:
        # Extract room ID from URL if it's a full URL, otherwise use as-is
        room_id = meeting.meeting_room_url.split("/")[-1] if "/" in meeting.meeting_room_url else meeting.meeting_room_url
    
    return {
        "room_id": room_id,
        "meeting_id": meeting.id,
        "meeting_title": meeting.title,
        "participant_count": len(room_manager.rooms.get(room_id, set()))
    }

