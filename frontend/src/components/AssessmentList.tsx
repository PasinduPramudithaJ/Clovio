import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Plus, Trash2, Star, User, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
import { useAuthStore } from '@/store/authStore';

interface Assessment {
  id: number;
  project_id: number;
  evaluated_user_id: number;
  evaluated_user_name: string;
  evaluator_id: number;
  evaluator_name: string;
  evaluation_type: 'professor' | 'peer' | 'self';
  overall_score: number;
  technical_skills?: number;
  collaboration?: number;
  communication?: number;
  problem_solving?: number;
  comments?: string;
  created_at: string;
  updated_at?: string;
}

interface ProjectMember {
  id: number;
  full_name: string;
  email: string;
}

export default function AssessmentList({ projectId }: { projectId: number }) {
  const { user } = useAuthStore();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAssessment, setNewAssessment] = useState({
    evaluated_user_id: '',
    evaluation_type: 'peer' as 'professor' | 'peer' | 'self',
    overall_score: '',
    technical_skills: '',
    collaboration: '',
    communication: '',
    problem_solving: '',
    comments: '',
  });

  useEffect(() => {
    fetchAssessments();
    fetchMembers();
  }, [projectId]);

  const fetchAssessments = async () => {
    try {
      const response = await api.get(`/api/assessments/?project_id=${projectId}`);
      setAssessments(response.data);
    } catch (error) {
      console.error('Failed to fetch assessments:', error);
      toast.error('Failed to load assessments');
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

  const handleCreateAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // For self-assessment, use current user's ID
    const evaluatedUserId = newAssessment.evaluation_type === 'self' 
      ? (user?.id || 0)
      : parseInt(newAssessment.evaluated_user_id);
    
    if (!evaluatedUserId) {
      toast.error('Please select a member to evaluate');
      return;
    }
    
    try {
      const assessmentData = {
        project_id: projectId,
        evaluated_user_id: evaluatedUserId,
        evaluation_type: newAssessment.evaluation_type,
        overall_score: parseFloat(newAssessment.overall_score),
        technical_skills: newAssessment.technical_skills ? parseFloat(newAssessment.technical_skills) : undefined,
        collaboration: newAssessment.collaboration ? parseFloat(newAssessment.collaboration) : undefined,
        communication: newAssessment.communication ? parseFloat(newAssessment.communication) : undefined,
        problem_solving: newAssessment.problem_solving ? parseFloat(newAssessment.problem_solving) : undefined,
        comments: newAssessment.comments || undefined,
      };

      await api.post(`/api/projects/${projectId}/assessments`, assessmentData);
      toast.success('Assessment created successfully!');
      setShowCreateModal(false);
      setNewAssessment({
        evaluated_user_id: '',
        evaluation_type: 'peer',
        overall_score: '',
        technical_skills: '',
        collaboration: '',
        communication: '',
        problem_solving: '',
        comments: '',
      });
      fetchAssessments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create assessment');
    }
  };

  const handleDelete = async (assessmentId: number) => {
    if (!confirm('Are you sure you want to delete this assessment?')) return;

    try {
      await api.delete(`/api/assessments/${assessmentId}`);
      toast.success('Assessment deleted');
      fetchAssessments();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete assessment');
    }
  };

  const getEvaluationTypeColor = (type: string) => {
    switch (type) {
      case 'professor':
        return 'bg-purple-100 text-purple-800';
      case 'peer':
        return 'bg-blue-100 text-blue-800';
      case 'self':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const canCreateAssessment = user?.role === 'professor' || user?.role === 'admin' || 
    members.some(m => m.id === user?.id);

  const canDeleteAssessment = (assessment: Assessment) => {
    return assessment.evaluator_id === user?.id || user?.role === 'professor' || user?.role === 'admin';
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
        <h2 className="text-xl font-bold text-gray-900">Assessments</h2>
        {canCreateAssessment && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={20} />
            New Assessment
          </button>
        )}
      </div>

      {assessments.length === 0 ? (
        <div className="card text-center py-12">
          <Star className="mx-auto text-gray-400 mb-4" size={48} />
          <p className="text-gray-600">No assessments yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {assessments.map((assessment) => (
            <div key={assessment.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <User className="text-primary-600" size={20} />
                    <div>
                      <p className="font-semibold text-gray-900">
                        {assessment.evaluated_user_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        Evaluated by {assessment.evaluator_name}
                      </p>
                    </div>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getEvaluationTypeColor(
                        assessment.evaluation_type
                      )}`}
                    >
                      {assessment.evaluation_type.charAt(0).toUpperCase() + assessment.evaluation_type.slice(1)}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-6 mt-3">
                    <div>
                      <p className="text-xs text-gray-500">Overall Score</p>
                      <div className="flex items-center gap-1">
                        <Star className="text-yellow-500 fill-yellow-500" size={16} />
                        <span className="font-semibold text-lg">{assessment.overall_score}/100</span>
                      </div>
                    </div>
                    {assessment.technical_skills !== null && assessment.technical_skills !== undefined && (
                      <div>
                        <p className="text-xs text-gray-500">Technical Skills</p>
                        <span className="font-medium">{assessment.technical_skills}/100</span>
                      </div>
                    )}
                    {assessment.collaboration !== null && assessment.collaboration !== undefined && (
                      <div>
                        <p className="text-xs text-gray-500">Collaboration</p>
                        <span className="font-medium">{assessment.collaboration}/100</span>
                      </div>
                    )}
                    {assessment.communication !== null && assessment.communication !== undefined && (
                      <div>
                        <p className="text-xs text-gray-500">Communication</p>
                        <span className="font-medium">{assessment.communication}/100</span>
                      </div>
                    )}
                    {assessment.problem_solving !== null && assessment.problem_solving !== undefined && (
                      <div>
                        <p className="text-xs text-gray-500">Problem Solving</p>
                        <span className="font-medium">{assessment.problem_solving}/100</span>
                      </div>
                    )}
                  </div>

                  {assessment.comments && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-sm text-gray-700">{assessment.comments}</p>
                    </div>
                  )}

                  <p className="text-xs text-gray-400 mt-3">
                    {format(new Date(assessment.created_at), 'MMM d, yyyy')}
                    {assessment.updated_at && assessment.updated_at !== assessment.created_at && (
                      <span> • Updated {format(new Date(assessment.updated_at), 'MMM d, yyyy')}</span>
                    )}
                  </p>
                </div>
                {canDeleteAssessment(assessment) && (
                  <button
                    onClick={() => handleDelete(assessment.id)}
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

      {/* Create Assessment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create Assessment</h2>
              <form onSubmit={handleCreateAssessment} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Evaluation Type
                  </label>
                  <select
                    value={newAssessment.evaluation_type}
                    onChange={(e) => {
                      const newType = e.target.value as 'professor' | 'peer' | 'self';
                      setNewAssessment({
                        ...newAssessment,
                        evaluation_type: newType,
                        evaluated_user_id: newType === 'self' ? (user?.id?.toString() || '') : newAssessment.evaluated_user_id,
                      });
                    }}
                    className="input-field"
                    disabled={user?.role !== 'professor' && user?.role !== 'admin'}
                  >
                    <option value="peer">Peer Assessment</option>
                    <option value="self">Self Assessment</option>
                    {(user?.role === 'professor' || user?.role === 'admin') && (
                      <option value="professor">Professor Assessment</option>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {newAssessment.evaluation_type === 'self' ? 'Self Assessment' : 'Evaluate Member'}
                  </label>
                  {newAssessment.evaluation_type === 'self' ? (
                    <input
                      type="text"
                      value={members.find(m => m.id === user?.id)?.full_name || 'Yourself'}
                      className="input-field"
                      disabled
                    />
                  ) : (
                    <select
                      value={newAssessment.evaluated_user_id}
                      onChange={(e) =>
                        setNewAssessment({ ...newAssessment, evaluated_user_id: e.target.value })
                      }
                      required
                      className="input-field"
                    >
                      <option value="">Select member</option>
                      {members
                        .filter((m) => m.id !== user?.id)
                        .map((member) => (
                          <option key={member.id} value={member.id}>
                            {member.full_name}
                          </option>
                        ))}
                    </select>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Overall Score (0-100)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={newAssessment.overall_score}
                    onChange={(e) =>
                      setNewAssessment({ ...newAssessment, overall_score: e.target.value })
                    }
                    required
                    className="input-field"
                    placeholder="e.g., 85.5"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Technical Skills (0-100)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={newAssessment.technical_skills}
                      onChange={(e) =>
                        setNewAssessment({ ...newAssessment, technical_skills: e.target.value })
                      }
                      className="input-field"
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Collaboration (0-100)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={newAssessment.collaboration}
                      onChange={(e) =>
                        setNewAssessment({ ...newAssessment, collaboration: e.target.value })
                      }
                      className="input-field"
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Communication (0-100)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={newAssessment.communication}
                      onChange={(e) =>
                        setNewAssessment({ ...newAssessment, communication: e.target.value })
                      }
                      className="input-field"
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Problem Solving (0-100)
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={newAssessment.problem_solving}
                      onChange={(e) =>
                        setNewAssessment({ ...newAssessment, problem_solving: e.target.value })
                      }
                      className="input-field"
                      placeholder="Optional"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Comments
                  </label>
                  <textarea
                    value={newAssessment.comments}
                    onChange={(e) =>
                      setNewAssessment({ ...newAssessment, comments: e.target.value })
                    }
                    rows={4}
                    className="input-field"
                    placeholder="Additional feedback..."
                  />
                </div>

                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Create Assessment
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

