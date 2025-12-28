import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Plus, Video, Calendar, MapPin, Trash2, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
import { useAuthStore } from '@/store/authStore';

interface Meeting {
  id: number;
  project_id: number;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  location?: string;
  meeting_type: string;
  meeting_room_url?: string;
  created_by_id: number;
  created_at: string;
}

interface ProjectMember {
  id: number;
  full_name: string;
  email: string;
}

export default function MeetingList({ projectId }: { projectId: number }) {
  const { user } = useAuthStore();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showVideoCall, setShowVideoCall] = useState(false);
  const [currentMeeting, setCurrentMeeting] = useState<Meeting | null>(null);
  const [newMeeting, setNewMeeting] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    location: '',
    meeting_type: 'virtual',
    meeting_room_url: '',
    participant_ids: [] as number[],
  });

  useEffect(() => {
    fetchMeetings();
    fetchMembers();
  }, [projectId]);

  const fetchMeetings = async () => {
    try {
      const response = await api.get(`/api/projects/${projectId}/meetings`);
      setMeetings(response.data);
    } catch (error) {
      console.error('Failed to fetch meetings:', error);
      toast.error('Failed to load meetings');
    } finally {
      setLoading(false);
    }
  };

  const fetchMembers = async () => {
    try {
      const response = await api.get(`/api/projects/${projectId}`);
      setMembers(response.data.members || []);
    } catch (error) {
      console.error('Failed to fetch members:', error);
    }
  };

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const meetingData = {
        project_id: projectId,
        title: newMeeting.title,
        description: newMeeting.description || undefined,
        start_time: new Date(newMeeting.start_time).toISOString(),
        end_time: new Date(newMeeting.end_time).toISOString(),
        location: newMeeting.location || undefined,
        meeting_type: newMeeting.meeting_type,
        meeting_room_url: newMeeting.meeting_room_url || undefined,
        participant_ids: newMeeting.participant_ids.length > 0 ? newMeeting.participant_ids : undefined,
      };

      await api.post(`/api/projects/${projectId}/meetings`, meetingData);
      toast.success('Meeting created successfully!');
      setShowCreateModal(false);
      setNewMeeting({
        title: '',
        description: '',
        start_time: '',
        end_time: '',
        location: '',
        meeting_type: 'virtual',
        meeting_room_url: '',
        participant_ids: [],
      });
      fetchMeetings();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create meeting');
    }
  };

  const handleDelete = async (meetingId: number) => {
    if (!confirm('Are you sure you want to delete this meeting?')) return;

    try {
      await api.delete(`/api/scheduling/meetings/${meetingId}`);
      toast.success('Meeting deleted');
      fetchMeetings();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete meeting');
    }
  };

  const handleJoinCall = (meeting: Meeting) => {
    if (meeting.meeting_type === 'in_person') {
      toast.info('This is an in-person meeting. Please check the location.');
      return;
    }
    
    setCurrentMeeting(meeting);
    setShowVideoCall(true);
  };

  const getMeetingTypeColor = (type: string) => {
    switch (type) {
      case 'virtual':
        return 'bg-blue-100 text-blue-800';
      case 'in_person':
        return 'bg-green-100 text-green-800';
      case 'hybrid':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const isUpcoming = (meeting: Meeting) => {
    return new Date(meeting.start_time) > new Date();
  };

  const canDeleteMeeting = (meeting: Meeting) => {
    return meeting.created_by_id === user?.id || user?.role === 'professor' || user?.role === 'admin';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Meetings</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={20} />
          Schedule Meeting
        </button>
      </div>

      {meetings.length === 0 ? (
        <div className="card text-center py-12">
          <Calendar className="mx-auto text-gray-400 mb-4" size={48} />
          <p className="text-gray-600">No meetings scheduled</p>
        </div>
      ) : (
        <div className="space-y-3">
          {meetings.map((meeting) => (
            <div key={meeting.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-gray-900 text-lg">{meeting.title}</h3>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getMeetingTypeColor(
                        meeting.meeting_type
                      )}`}
                    >
                      {meeting.meeting_type.charAt(0).toUpperCase() + meeting.meeting_type.slice(1).replace('_', ' ')}
                    </span>
                    {isUpcoming(meeting) && (
                      <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                        Upcoming
                      </span>
                    )}
                  </div>
                  
                  {meeting.description && (
                    <p className="text-sm text-gray-600 mb-3">{meeting.description}</p>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Calendar size={16} />
                      <span>
                        {format(new Date(meeting.start_time), 'MMM d, yyyy h:mm a')} -{' '}
                        {format(new Date(meeting.end_time), 'h:mm a')}
                      </span>
                    </div>
                    {meeting.location && (
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <MapPin size={16} />
                        <span>{meeting.location}</span>
                      </div>
                    )}
                    {meeting.meeting_room_url && (
                      <div className="flex items-center gap-2 text-sm text-primary-600">
                        <Video size={16} />
                        <span>Room: {meeting.meeting_room_url}</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {meeting.meeting_type !== 'in_person' && meeting.meeting_room_url && (
                    <button
                      onClick={() => handleJoinCall(meeting)}
                      className="btn-primary flex items-center gap-2 text-sm"
                    >
                      <Video size={16} />
                      Join Call
                    </button>
                  )}
                  {canDeleteMeeting(meeting) && (
                    <button
                      onClick={() => handleDelete(meeting.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 size={20} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Meeting Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Schedule Meeting</h2>
              <form onSubmit={handleCreateMeeting} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={newMeeting.title}
                    onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                    required
                    className="input-field"
                    placeholder="Meeting title"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newMeeting.description}
                    onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                    rows={3}
                    className="input-field"
                    placeholder="Meeting description (optional)"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                    <input
                      type="datetime-local"
                      value={newMeeting.start_time}
                      onChange={(e) => setNewMeeting({ ...newMeeting, start_time: e.target.value })}
                      required
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                    <input
                      type="datetime-local"
                      value={newMeeting.end_time}
                      onChange={(e) => setNewMeeting({ ...newMeeting, end_time: e.target.value })}
                      required
                      className="input-field"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Meeting Type</label>
                  <select
                    value={newMeeting.meeting_type}
                    onChange={(e) => setNewMeeting({ ...newMeeting, meeting_type: e.target.value })}
                    className="input-field"
                  >
                    <option value="virtual">Virtual</option>
                    <option value="in_person">In Person</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                </div>

                {(newMeeting.meeting_type === 'virtual' || newMeeting.meeting_type === 'hybrid') && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Meeting Room URL (optional - will be auto-generated if not provided)
                    </label>
                    <input
                      type="text"
                      value={newMeeting.meeting_room_url}
                      onChange={(e) => setNewMeeting({ ...newMeeting, meeting_room_url: e.target.value })}
                      className="input-field"
                      placeholder="e.g., https://meet.google.com/xxx-xxxx-xxx or Zoom link"
                    />
                  </div>
                )}

                {newMeeting.meeting_type === 'in_person' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
                    <input
                      type="text"
                      value={newMeeting.location}
                      onChange={(e) => setNewMeeting({ ...newMeeting, location: e.target.value })}
                      className="input-field"
                      placeholder="Physical location"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Participants (leave empty to include all project members)
                  </label>
                  <div className="space-y-2 max-h-32 overflow-y-auto border border-gray-300 rounded-lg p-2">
                    {members.map((member) => (
                      <label key={member.id} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={newMeeting.participant_ids.includes(member.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setNewMeeting({
                                ...newMeeting,
                                participant_ids: [...newMeeting.participant_ids, member.id],
                              });
                            } else {
                              setNewMeeting({
                                ...newMeeting,
                                participant_ids: newMeeting.participant_ids.filter((id) => id !== member.id),
                              });
                            }
                          }}
                          className="rounded"
                        />
                        <span className="text-sm">{member.full_name}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Schedule Meeting
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="btn-secondary flex-1"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Video Call Modal */}
      {showVideoCall && currentMeeting && (
        <VideoCallModal
          meeting={currentMeeting}
          onClose={() => {
            setShowVideoCall(false);
            setCurrentMeeting(null);
          }}
        />
      )}
    </div>
  );
}

// Simple Video Call Component (can be replaced with Daily.co, Twilio, or custom WebRTC)
function VideoCallModal({ meeting, onClose }: { meeting: Meeting; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full m-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{meeting.title}</h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <XCircle size={24} />
            </button>
          </div>
          
          <div className="bg-gray-900 rounded-lg p-8 text-center mb-4">
            <Video className="mx-auto text-white mb-4" size={64} />
            <p className="text-white text-lg mb-2">Video Call</p>
            <p className="text-gray-400 text-sm mb-4">
              {meeting.meeting_room_url || 'Meeting Room'}
            </p>
            <div className="space-y-2">
              <p className="text-gray-300 text-sm">
                To join this call, use the meeting room URL:
              </p>
              <p className="text-primary-400 font-mono text-sm break-all">
                {meeting.meeting_room_url || '/meeting/room'}
              </p>
              <p className="text-gray-400 text-xs mt-4">
                Note: For production, integrate with a video calling service like Daily.co, Twilio, or Zoom API
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => {
                if (meeting.meeting_room_url) {
                  window.open(meeting.meeting_room_url, '_blank');
                } else {
                  toast.info('Meeting room URL not available');
                }
              }}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <Video size={20} />
              Open in New Tab
            </button>
            <button onClick={onClose} className="btn-secondary flex-1">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

