import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import {
  Calendar,
  Users,
  FileText,
  MessageSquare,
  Plus,
  Bot,
  CheckCircle2,
  Clock,
  AlertCircle,
  Timer,
  Trash2,
  X,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import toast from 'react-hot-toast';
import ProjectChat from '@/components/ProjectChat';
import DocumentList from '@/components/DocumentList';
import AssessmentList from '@/components/AssessmentList';
import MeetingList from '@/components/MeetingList';
import ContributionList from '@/components/ContributionList';
import WorkloadDistribution from '@/components/WorkloadDistribution';

interface Project {
  id: number;
  title: string;
  description: string;
  deadline: string;
  course_code?: string;
  course_name?: string;
  created_by_id?: number;
  members: Array<{ id: number; full_name: string; email: string; role?: string; member_role?: string }>;
  tasks: Task[];
  document_count: number;
  message_count: number;
  assessment_count: number;
  meeting_count: number;
  contribution_count: number;
}

interface Task {
  id: number;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assigned_to_id?: number;
  due_date?: string;
  estimated_hours?: number;
  actual_hours: number;
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'tasks' | 'chat' | 'documents' | 'schedule' | 'contributions' | 'assessments'>('tasks');
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [showTimeLogModal, setShowTimeLogModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState<number | null>(null);
  const [timeLogs, setTimeLogs] = useState<Record<number, any[]>>({});
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium',
    due_date: '',
  });
  const [newTimeLog, setNewTimeLog] = useState({
    hours: '',
    description: '',
  });
  const { user } = useAuthStore();
  const isProfessor = user?.role === 'professor';
  const isAdmin = user?.role === 'admin';

  useEffect(() => {
    if (id) {
      fetchProject();
    }
  }, [id]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/api/projects/${id}`);
      // Ensure all required fields have default values
      const projectData = {
        ...response.data,
        meeting_count: response.data.meeting_count || 0,
        contribution_count: response.data.contribution_count || 0,
        assessment_count: response.data.assessment_count || 0,
        document_count: response.data.document_count || 0,
        message_count: response.data.message_count || 0,
      };
      setProject(projectData);
      
      // Check if user is enrolled - if not, show message
      const isEnrolled = projectData.members?.some((m: any) => m.id === user?.id);
      if (!isEnrolled && !isProfessor) {
        // User can see project but tasks will be empty
      }
    } catch (error: any) {
      console.error('Failed to fetch project:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to load project';
      toast.error(errorMessage);
      // Only navigate if it's a 404 or 403 error
      if (error.response?.status === 404 || error.response?.status === 403) {
        navigate('/projects');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Students automatically assign tasks to themselves
      const taskData: any = {
        ...newTask,
        project_id: parseInt(id!),
      };
      
      // If user is a student, assign to themselves
      if (!isProfessor && user?.id) {
        taskData.assigned_to_id = user.id;
      }
      
      await api.post('/api/tasks/', taskData);
      toast.success('Task created successfully!');
      setShowTaskModal(false);
      setNewTask({ title: '', description: '', priority: 'medium', due_date: '' });
      fetchProject();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create task');
    }
  };

  const handleBreakdown = async () => {
    try {
      toast.loading('Breaking down project into tasks and assigning based on skills...', { id: 'breakdown' });
      await api.post(`/api/projects/${id}/breakdown`);
      toast.success('Project broken down into tasks! Tasks will be automatically assigned to team members based on their skills.', { id: 'breakdown' });
      fetchProject();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to break down project', { id: 'breakdown' });
    }
  };

  const handleUpdateTaskStatus = async (taskId: number, status: string) => {
    try {
      await api.patch(`/api/tasks/${taskId}`, { status });
      toast.success('Task updated!');
      fetchProject();
    } catch (error: any) {
      toast.error('Failed to update task');
    }
  };

  const handleAssignToSelf = async (taskId: number) => {
    try {
      await api.patch(`/api/tasks/${taskId}`, { assigned_to_id: user?.id });
      toast.success('Task assigned to you!');
      fetchProject();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to assign task');
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('Are you sure you want to delete this task? This action cannot be undone.')) return;
    
    try {
      await api.delete(`/api/tasks/${taskId}`);
      toast.success('Task deleted successfully!');
      fetchProject();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete task');
    }
  };

  // Check if current user is project leader
  const isProjectLeader = project?.members?.some(
    (m: any) => m.id === user?.id && (m.member_role === 'leader' || m.role === 'leader')
  ) || project?.created_by_id === user?.id;

  // Check if user can delete tasks (professors/admins or project leaders)
  const canDeleteTask = isProfessor || isAdmin || isProjectLeader;

  const handleLogTime = async (taskId: number) => {
    setSelectedTask(taskId);
    setShowTimeLogModal(true);
    // Fetch existing time logs
    try {
      const response = await api.get(`/api/tasks/${taskId}/time-logs`);
      setTimeLogs({ ...timeLogs, [taskId]: response.data });
    } catch (error) {
      console.error('Failed to fetch time logs:', error);
    }
  };

  const handleSubmitTimeLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;
    
    try {
      await api.post('/api/tasks/log-time', {
        task_id: selectedTask,
        hours: parseFloat(newTimeLog.hours),
        description: newTimeLog.description,
      });
      toast.success('Time logged successfully!');
      setShowTimeLogModal(false);
      setNewTimeLog({ hours: '', description: '' });
      fetchProject();
      // Refresh time logs
      const response = await api.get(`/api/tasks/${selectedTask}/time-logs`);
      setTimeLogs({ ...timeLogs, [selectedTask]: response.data });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to log time');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="text-green-600" size={20} />;
      case 'in_progress':
        return <Clock className="text-blue-600" size={20} />;
      default:
        return <AlertCircle className="text-gray-400" size={20} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!project) {
    return <div>Project not found</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/projects')}
          className="text-primary-600 hover:text-primary-700 mb-4"
        >
          ← Back to Projects
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{project.title}</h1>
            {project.course_code && (
              <p className="text-primary-600 font-medium mt-1">{project.course_code}</p>
            )}
            <p className="text-gray-600 mt-2">{project.description}</p>
          </div>
          {!isProfessor && project.members?.some((m: any) => m.id === user?.id) && (
            <button onClick={handleBreakdown} className="btn-primary flex items-center gap-2">
              <Bot size={20} />
              AI Breakdown
            </button>
          )}
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-6 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <Calendar size={16} />
              <span>Due: {new Date(project.deadline).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users size={16} />
              <span>{project.members.length} members</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!isProfessor && project.members?.some((m: any) => m.id === user?.id) && (
              <button
                onClick={async () => {
                  if (!confirm('Are you sure you want to unenroll from this project?')) return;
                  try {
                    await api.delete(`/api/projects/${id}/enroll`);
                    toast.success('Successfully unenrolled from project!');
                    navigate('/projects');
                  } catch (error: any) {
                    toast.error(error.response?.data?.detail || 'Failed to unenroll');
                  }
                }}
                className="btn-secondary text-red-600 hover:bg-red-50"
              >
                Unenroll
              </button>
            )}
            {!isProfessor && !project.members?.some((m: any) => m.id === user?.id) && (
              <button
                onClick={async () => {
                  try {
                    await api.post(`/api/projects/${id}/enroll`);
                    toast.success('Successfully enrolled in project!');
                    fetchProject();
                  } catch (error: any) {
                    toast.error(error.response?.data?.detail || 'Failed to enroll');
                  }
                }}
                className="btn-primary"
              >
                Enroll in Project
              </button>
            )}
            {isAdmin && (
              <button
                onClick={async () => {
                  if (!confirm('Are you sure you want to delete this project? This will permanently delete all tasks, documents, chat messages, and other related data. This action cannot be undone.')) return;
                  try {
                    await api.delete(`/api/projects/${id}`);
                    toast.success('Project deleted successfully!');
                    navigate('/projects');
                  } catch (error: any) {
                    toast.error(error.response?.data?.detail || 'Failed to delete project');
                  }
                }}
                className="btn-secondary text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <Trash2 size={16} />
                Delete Project
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6 overflow-x-auto">
          {[
            { id: 'tasks', label: 'Tasks', count: project.tasks.length },
            { id: 'chat', label: 'Chat', count: project.message_count },
            { id: 'documents', label: 'Documents', count: project.document_count },
            { id: 'schedule', label: 'Schedule', count: project.meeting_count || 0 },
            { id: 'contributions', label: 'Contributions', count: project.contribution_count || 0 },
            { id: 'assessments', label: 'Assessments', count: project.assessment_count || 0 },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-4 px-1 border-b-2 font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label} {tab.count > 0 && `(${tab.count})`}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'tasks' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-gray-900">Tasks</h2>
            <button
              onClick={() => setShowTaskModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus size={20} />
              New Task
            </button>
          </div>

          {project.tasks.length === 0 ? (
            <div className="card text-center py-12">
              {project.members?.some((m: any) => m.id === user?.id) || isProfessor ? (
                <>
                  <p className="text-gray-600 mb-4">
                    {isProfessor 
                      ? 'No tasks yet. Tasks are automatically created when students create projects.' 
                      : 'No tasks yet'}
                  </p>
                  {!isProfessor && project.members?.some((m: any) => m.id === user?.id) && (
                    <button onClick={handleBreakdown} className="btn-primary">
                      Use AI to break down project
                    </button>
                  )}
                </>
              ) : (
                <>
                  <p className="text-gray-600 mb-4">You need to enroll in this project to see tasks</p>
                  <button
                    onClick={async () => {
                      try {
                        await api.post(`/api/projects/${id}/enroll`);
                        toast.success('Successfully enrolled!');
                        fetchProject();
                      } catch (error: any) {
                        toast.error(error.response?.data?.detail || 'Failed to enroll');
                      }
                    }}
                    className="btn-primary"
                  >
                    Enroll in Project
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {project.tasks.map((task) => (
                <div key={task.id} className="card">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getStatusIcon(task.status)}
                        <h3 className="font-semibold text-gray-900">{task.title}</h3>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            task.priority === 'high' || task.priority === 'urgent'
                              ? 'bg-red-100 text-red-800'
                              : task.priority === 'medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {task.priority}
                        </span>
                      </div>
                      {task.description && (
                        <p className="text-sm text-gray-600 mb-2">{task.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        {task.due_date && (
                          <span>Due: {new Date(task.due_date).toLocaleDateString()}</span>
                        )}
                        {task.estimated_hours && <span>Est: {task.estimated_hours}h</span>}
                        {task.actual_hours > 0 && <span>Actual: {task.actual_hours}h</span>}
                      </div>
                      {!task.assigned_to_id && !isProfessor && (
                        <button
                          onClick={() => handleAssignToSelf(task.id)}
                          className="mt-2 text-xs text-primary-600 hover:text-primary-700"
                        >
                          Assign to me
                        </button>
                      )}
                      {task.assigned_to_id === user?.id && (
                        <button
                          onClick={() => handleLogTime(task.id)}
                          className="mt-2 flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700"
                        >
                          <Timer size={14} />
                          Log Time
                        </button>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      <select
                        value={task.status}
                        onChange={(e) => handleUpdateTaskStatus(task.id, e.target.value)}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm"
                        disabled={!task.assigned_to_id || (task.assigned_to_id !== user?.id && !isProfessor)}
                      >
                        <option value="todo">To Do</option>
                        <option value="in_progress">In Progress</option>
                        <option value="review">Review</option>
                        <option value="completed">Completed</option>
                      </select>
                      {canDeleteTask && (
                        <button
                          onClick={() => handleDeleteTask(task.id)}
                          className="px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded-lg border border-red-200 hover:border-red-300 flex items-center justify-center gap-1 transition-colors"
                          title="Delete task"
                        >
                          <X size={14} />
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                  {timeLogs[task.id] && timeLogs[task.id].length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-medium text-gray-700 mb-2">Time Logs:</p>
                      <div className="space-y-1">
                        {timeLogs[task.id].map((log) => (
                          <div key={log.id} className="text-xs text-gray-600">
                            {log.user_name}: {log.hours}h
                            {log.description && ` - ${log.description}`}
                            <span className="text-gray-400 ml-2">
                              {new Date(log.logged_date).toLocaleDateString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'chat' && <ProjectChat projectId={parseInt(id!)} />}
      {activeTab === 'documents' && <DocumentList projectId={parseInt(id!)} />}
      
      {activeTab === 'schedule' && <MeetingList projectId={parseInt(id!)} />}
      
      {activeTab === 'contributions' && <ContributionList projectId={parseInt(id!)} />}
      
      {activeTab === 'assessments' && <AssessmentList projectId={parseInt(id!)} />}
      
      {/* Workload Distribution - Show in analytics or separate section */}
      {activeTab === 'tasks' && project.tasks.length > 0 && (
        <div className="mt-8">
          <WorkloadDistribution projectId={parseInt(id!)} />
        </div>
      )}

      {/* Time Log Modal */}
      {showTimeLogModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Log Time</h2>
              <form onSubmit={handleSubmitTimeLog} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    value={newTimeLog.hours}
                    onChange={(e) => setNewTimeLog({ ...newTimeLog, hours: e.target.value })}
                    required
                    placeholder="e.g., 2.5"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
                  <textarea
                    value={newTimeLog.description}
                    onChange={(e) => setNewTimeLog({ ...newTimeLog, description: e.target.value })}
                    rows={3}
                    placeholder="What did you work on?"
                    className="input-field"
                  />
                </div>
                {selectedTask && timeLogs[selectedTask] && timeLogs[selectedTask].length > 0 && (
                  <div className="border-t pt-4">
                    <p className="text-sm font-medium text-gray-700 mb-2">Previous Logs:</p>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {timeLogs[selectedTask].map((log) => (
                        <div key={log.id} className="text-xs text-gray-600">
                          {log.hours}h - {log.description || 'No description'}
                          <span className="text-gray-400 ml-2">
                            {new Date(log.logged_date).toLocaleDateString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Log Time
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowTimeLogModal(false);
                      setNewTimeLog({ hours: '', description: '' });
                      setSelectedTask(null);
                    }}
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

      {/* Create Task Modal */}
      {showTaskModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Task</h2>
              <form onSubmit={handleCreateTask} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={newTask.title}
                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                    required
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newTask.description}
                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                    rows={3}
                    className="input-field"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                    <select
                      value={newTask.priority}
                      onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                      className="input-field"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                    <input
                      type="datetime-local"
                      value={newTask.due_date}
                      onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                      className="input-field"
                    />
                  </div>
                </div>
                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Create Task
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowTaskModal(false)}
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
    </div>
  );
}

