import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { Plus, Calendar, Users, Search, UserPlus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/store/authStore';

interface Project {
  id: number;
  title: string;
  description: string;
  deadline: string;
  status: string;
  course_code?: string;
  created_at: string;
  members?: Array<{ id: number; full_name: string }>;
}

export default function Projects() {
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const isProfessor = user?.role === 'professor';
  const isAdmin = user?.role === 'admin';
  const isStudent = user?.role === 'student';
  const [newProject, setNewProject] = useState({
    title: '',
    description: '',
    course_code: '',
    course_name: '',
    deadline: '',
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await api.get('/api/projects/');
      const projectsData = response.data;
      
      // Fetch members for each project to check enrollment status
      const projectsWithMembers = await Promise.all(
        projectsData.map(async (project: Project) => {
          try {
            const projectDetail = await api.get(`/api/projects/${project.id}`);
            return {
              ...project,
              members: projectDetail.data.members || [],
            };
          } catch {
            return { ...project, members: [] };
          }
        })
      );
      
      setProjects(projectsWithMembers);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      toast.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      toast.loading('Creating project and generating tasks...', { id: 'create-project' });
      await api.post('/api/projects/', newProject);
      toast.success('Project created successfully! Tasks have been automatically generated and assigned based on team member skills.', { id: 'create-project' });
      setShowCreateModal(false);
      setNewProject({
        title: '',
        description: '',
        course_code: '',
        course_name: '',
        deadline: '',
      });
      fetchProjects();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create project', { id: 'create-project' });
    }
  };

  const handleEnroll = async (projectId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.post(`/api/projects/${projectId}/enroll`);
      toast.success('Successfully enrolled in project!');
      fetchProjects();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to enroll in project');
    }
  };

  const handleUnenroll = async (projectId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to unenroll from this project?')) return;
    
    try {
      await api.delete(`/api/projects/${projectId}/enroll`);
      toast.success('Successfully unenrolled from project!');
      fetchProjects();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to unenroll from project');
    }
  };

  const handleDeleteProject = async (projectId: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this project? This will delete all tasks, documents, and other related data. This action cannot be undone.')) return;
    
    try {
      await api.delete(`/api/projects/${projectId}`);
      toast.success('Project deleted successfully!');
      fetchProjects();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete project');
    }
  };

  const isEnrolled = (project: Project): boolean => {
    if (!user?.id || !project.members) return false;
    return project.members.some(member => member.id === user.id);
  };

  const filteredProjects = projects.filter(
    (project) =>
      project.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      project.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      project.course_code?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-2">
            {isProfessor 
              ? 'View project progress and analytics' 
              : 'Manage your academic projects'}
          </p>
          {isProfessor && (
            <p className="text-sm text-blue-600 mt-1">
              Note: Professors can view project progress but cannot create or delete projects.
            </p>
          )}
        </div>
        {isStudent && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={20} />
            New Project
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
        <input
          type="text"
          placeholder="Search projects..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field pl-10"
        />
      </div>

      {/* Projects Grid */}
      {filteredProjects.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600">No projects found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="card hover:shadow-lg transition-shadow"
            >
              <h3 className="text-xl font-bold text-gray-900 mb-2">{project.title}</h3>
              {project.course_code && (
                <p className="text-sm text-primary-600 font-medium mb-2">{project.course_code}</p>
              )}
              <p className="text-gray-600 text-sm line-clamp-3 mb-4">{project.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <Calendar size={16} />
                    <span>{new Date(project.deadline).toLocaleDateString()}</span>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      project.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {project.status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {!isProfessor && (
                    isEnrolled(project) ? (
                      <button
                        onClick={(e) => handleUnenroll(project.id, e)}
                        className="btn-secondary flex items-center gap-1 text-xs px-3 py-1 bg-red-50 text-red-600 hover:bg-red-100"
                      >
                        Unenroll
                      </button>
                    ) : (
                      <button
                        onClick={(e) => handleEnroll(project.id, e)}
                        className="btn-secondary flex items-center gap-1 text-xs px-3 py-1"
                      >
                        <UserPlus size={14} />
                        Enroll
                      </button>
                    )
                  )}
                  {isAdmin && (
                    <button
                      onClick={(e) => handleDeleteProject(project.id, e)}
                      className="btn-secondary flex items-center gap-1 text-xs px-3 py-1 bg-red-50 text-red-600 hover:bg-red-100"
                      title="Delete project"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Project</h2>
              <form onSubmit={handleCreateProject} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={newProject.title}
                    onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                    required
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={newProject.description}
                    onChange={(e) =>
                      setNewProject({ ...newProject, description: e.target.value })
                    }
                    required
                    rows={4}
                    className="input-field"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Course Code</label>
                    <input
                      type="text"
                      value={newProject.course_code}
                      onChange={(e) =>
                        setNewProject({ ...newProject, course_code: e.target.value })
                      }
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Deadline</label>
                    <input
                      type="datetime-local"
                      value={newProject.deadline}
                      onChange={(e) =>
                        setNewProject({ ...newProject, deadline: e.target.value })
                      }
                      required
                      className="input-field"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Course Name</label>
                  <input
                    type="text"
                    value={newProject.course_name}
                    onChange={(e) =>
                      setNewProject({ ...newProject, course_name: e.target.value })
                    }
                    className="input-field"
                  />
                </div>
                <div className="flex gap-4 pt-4">
                  <button type="submit" className="btn-primary flex-1">
                    Create Project
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

