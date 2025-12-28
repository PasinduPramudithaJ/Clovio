import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Plus, Code, FileText, Palette, Search, Trash2, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
import { useAuthStore } from '@/store/authStore';

interface Contribution {
  id: number;
  project_id: number;
  user_id: number;
  user_name: string;
  task_id?: number;
  contribution_type: string;
  description: string;
  hours_spent: number;
  created_at: string;
}

interface Task {
  id: number;
  title: string;
}

export default function ContributionList({ projectId }: { projectId: number }) {
  const { user } = useAuthStore();
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newContribution, setNewContribution] = useState({
    task_id: '',
    contribution_type: 'code',
    description: '',
    hours_spent: '',
  });

  useEffect(() => {
    fetchContributions();
    fetchTasks();
  }, [projectId]);

  const fetchContributions = async () => {
    try {
      const response = await api.get(`/api/projects/${projectId}/contributions`);
      setContributions(response.data);
    } catch (error) {
      console.error('Failed to fetch contributions:', error);
      toast.error('Failed to load contributions');
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await api.get(`/api/projects/${projectId}`);
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const handleCreateContribution = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const contributionData = {
        project_id: projectId,
        task_id: newContribution.task_id ? parseInt(newContribution.task_id) : undefined,
        contribution_type: newContribution.contribution_type,
        description: newContribution.description,
        hours_spent: parseFloat(newContribution.hours_spent) || 0,
      };

      await api.post(`/api/projects/${projectId}/contributions`, contributionData);
      toast.success('Contribution recorded successfully!');
      setShowCreateModal(false);
      setNewContribution({
        task_id: '',
        contribution_type: 'code',
        description: '',
        hours_spent: '',
      });
      fetchContributions();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to record contribution');
    }
  };

  const handleDelete = async (contributionId: number) => {
    if (!confirm('Are you sure you want to delete this contribution?')) return;

    try {
      await api.delete(`/api/contributions/${contributionId}`);
      toast.success('Contribution deleted');
      fetchContributions();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete contribution');
    }
  };

  const getContributionTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'code':
        return <Code size={20} className="text-blue-600" />;
      case 'documentation':
        return <FileText size={20} className="text-green-600" />;
      case 'design':
        return <Palette size={20} className="text-purple-600" />;
      case 'research':
        return <Search size={20} className="text-orange-600" />;
      default:
        return <FileText size={20} className="text-gray-600" />;
    }
  };

  const getContributionTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'code':
        return 'bg-blue-100 text-blue-800';
      case 'documentation':
        return 'bg-green-100 text-green-800';
      case 'design':
        return 'bg-purple-100 text-purple-800';
      case 'research':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const canDeleteContribution = (contribution: Contribution) => {
    return contribution.user_id === user?.id || user?.role === 'professor' || user?.role === 'admin';
  };

  const totalHours = contributions.reduce((sum, contrib) => sum + contrib.hours_spent, 0);
  const userContributions = contributions.filter(c => c.user_id === user?.id);
  const userTotalHours = userContributions.reduce((sum, contrib) => sum + contrib.hours_spent, 0);

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
        <div>
          <h2 className="text-xl font-bold text-gray-900">Contributions</h2>
          <p className="text-sm text-gray-600 mt-1">
            Total: {totalHours.toFixed(1)}h • Your contributions: {userTotalHours.toFixed(1)}h
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={20} />
          Record Contribution
        </button>
      </div>

      {contributions.length === 0 ? (
        <div className="card text-center py-12">
          <Code className="mx-auto text-gray-400 mb-4" size={48} />
          <p className="text-gray-600">No contributions recorded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {contributions.map((contribution) => (
            <div key={contribution.id} className="card">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-start gap-3 flex-1">
                  {getContributionTypeIcon(contribution.contribution_type)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-gray-900">{contribution.user_name}</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getContributionTypeColor(
                          contribution.contribution_type
                        )}`}
                      >
                        {contribution.contribution_type.charAt(0).toUpperCase() + contribution.contribution_type.slice(1)}
                      </span>
                      {contribution.hours_spent > 0 && (
                        <span className="flex items-center gap-1 text-sm text-gray-600">
                          <Clock size={14} />
                          {contribution.hours_spent}h
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{contribution.description}</p>
                    {contribution.task_id && (
                      <p className="text-xs text-gray-500">
                        Related to task #{contribution.task_id}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-2">
                      {format(new Date(contribution.created_at), 'MMM d, yyyy h:mm a')}
                    </p>
                  </div>
                </div>
                {canDeleteContribution(contribution) && (
                  <button
                    onClick={() => handleDelete(contribution.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 size={20} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Contribution Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Record Contribution</h2>
              <form onSubmit={handleCreateContribution} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Contribution Type
                  </label>
                  <select
                    value={newContribution.contribution_type}
                    onChange={(e) =>
                      setNewContribution({ ...newContribution, contribution_type: e.target.value })
                    }
                    required
                    className="input-field"
                  >
                    <option value="code">Code</option>
                    <option value="documentation">Documentation</option>
                    <option value="design">Design</option>
                    <option value="research">Research</option>
                    <option value="testing">Testing</option>
                    <option value="review">Code Review</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Related Task (Optional)
                  </label>
                  <select
                    value={newContribution.task_id}
                    onChange={(e) =>
                      setNewContribution({ ...newContribution, task_id: e.target.value })
                    }
                    className="input-field"
                  >
                    <option value="">No specific task</option>
                    {tasks.map((task) => (
                      <option key={task.id} value={task.id}>
                        {task.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={newContribution.description}
                    onChange={(e) =>
                      setNewContribution({ ...newContribution, description: e.target.value })
                    }
                    required
                    rows={4}
                    className="input-field"
                    placeholder="Describe what you contributed..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Hours Spent (Optional)
                  </label>
                  <input
                    type="number"
                    step="0.25"
                    min="0"
                    value={newContribution.hours_spent}
                    onChange={(e) =>
                      setNewContribution({ ...newContribution, hours_spent: e.target.value })
                    }
                    className="input-field"
                    placeholder="e.g., 2.5"
                  />
                </div>

                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Record Contribution
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
    </div>
  );
}

