import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Plus, Trash2, Award, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';

interface Skill {
  id: number;
  name: string;
  category: string;
  level: string;
  verified: boolean;
  created_at: string;
}

export default function Skills() {
  const { user } = useAuthStore();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newSkill, setNewSkill] = useState({
    name: '',
    category: 'technical',
    level: 'intermediate',
  });

  useEffect(() => {
    if (user?.id) {
      fetchSkills();
    }
  }, [user]);

  const fetchSkills = async () => {
    try {
      const response = await api.get(`/api/users/${user?.id}/skills`);
      setSkills(response.data);
    } catch (error) {
      console.error('Failed to fetch skills:', error);
      toast.error('Failed to load skills');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post(`/api/users/${user?.id}/skills`, newSkill);
      toast.success('Skill added successfully!');
      setShowAddModal(false);
      setNewSkill({ name: '', category: 'technical', level: 'intermediate' });
      fetchSkills();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add skill');
    }
  };

  const handleDeleteSkill = async (skillId: number) => {
    if (!confirm('Are you sure you want to delete this skill?')) return;
    
    try {
      await api.delete(`/api/users/${user?.id}/skills/${skillId}`);
      toast.success('Skill deleted successfully!');
      fetchSkills();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete skill');
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'expert':
        return 'bg-purple-100 text-purple-800';
      case 'advanced':
        return 'bg-blue-100 text-blue-800';
      case 'intermediate':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'technical':
        return <Award className="text-blue-600" size={20} />;
      case 'soft':
        return <TrendingUp className="text-green-600" size={20} />;
      default:
        return <Award className="text-gray-600" size={20} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const skillsByCategory = {
    technical: skills.filter(s => s.category === 'technical'),
    soft: skills.filter(s => s.category === 'soft'),
    domain: skills.filter(s => s.category === 'domain'),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Skills</h1>
          <p className="text-gray-600 mt-2">Manage your skills and expertise</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus size={20} />
          Add Skill
        </button>
      </div>

      {/* Skills by Category */}
      {Object.entries(skillsByCategory).map(([category, categorySkills]) => {
        if (categorySkills.length === 0) return null;
        
        return (
          <div key={category} className="card">
            <div className="flex items-center gap-2 mb-4">
              {getCategoryIcon(category)}
              <h2 className="text-xl font-bold text-gray-900 capitalize">{category} Skills</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {categorySkills.map((skill) => (
                <div
                  key={skill.id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">{skill.name}</h3>
                    <button
                      onClick={() => handleDeleteSkill(skill.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getLevelColor(skill.level)}`}>
                      {skill.level}
                    </span>
                    {skill.verified && (
                      <span className="text-xs text-green-600 font-medium">✓ Verified</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {skills.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-gray-600 mb-4">No skills added yet</p>
          <button onClick={() => setShowAddModal(true)} className="btn-primary">
            Add Your First Skill
          </button>
        </div>
      )}

      {/* Add Skill Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-lg w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Add New Skill</h2>
              <form onSubmit={handleAddSkill} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Skill Name</label>
                  <input
                    type="text"
                    value={newSkill.name}
                    onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
                    required
                    placeholder="e.g., Python, JavaScript, Communication"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    value={newSkill.category}
                    onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value })}
                    className="input-field"
                  >
                    <option value="technical">Technical</option>
                    <option value="soft">Soft Skills</option>
                    <option value="domain">Domain Knowledge</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Proficiency Level</label>
                  <select
                    value={newSkill.level}
                    onChange={(e) => setNewSkill({ ...newSkill, level: e.target.value })}
                    className="input-field"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>
                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Add Skill
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
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

