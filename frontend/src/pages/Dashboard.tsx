import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { FolderKanban, Clock, CheckCircle2, AlertCircle, TrendingUp } from 'lucide-react';

interface Project {
  id: number;
  title: string;
  description: string;
  deadline: string;
  status: string;
}

interface Task {
  id: number;
  title: string;
  status: string;
  project_id: number;
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const isStudent = user?.role === 'student';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [projectsRes, tasksRes] = await Promise.all([
        api.get('/api/projects/?limit=5'),
        api.get('/api/tasks/?limit=10'),
      ]);
      setProjects(projectsRes.data);
      setTasks(tasksRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = {
    totalProjects: projects.length,
    activeTasks: tasks.filter((t) => t.status === 'in_progress').length,
    completedTasks: tasks.filter((t) => t.status === 'completed').length,
    pendingTasks: tasks.filter((t) => t.status === 'todo').length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user?.full_name}!</h1>
        <p className="text-gray-600 mt-2">Here's an overview of your academic projects</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Projects</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalProjects}</p>
            </div>
            <FolderKanban className="text-primary-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Tasks</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.activeTasks}</p>
            </div>
            <Clock className="text-blue-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completed</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.completedTasks}</p>
            </div>
            <CheckCircle2 className="text-green-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.pendingTasks}</p>
            </div>
            <AlertCircle className="text-yellow-600" size={32} />
          </div>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Recent Projects</h2>
          <Link to="/projects" className="text-primary-600 hover:text-primary-700 font-medium">
            View all
          </Link>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12">
            <FolderKanban className="mx-auto text-gray-400" size={48} />
            <p className="text-gray-600 mt-4">No projects yet</p>
            {isStudent && (
              <Link to="/projects" className="btn-primary mt-4 inline-block">
                Create Project
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{project.title}</h3>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">{project.description}</p>
                    <p className="text-xs text-gray-500 mt-2">
                      Deadline: {new Date(project.deadline).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-medium ${
                      project.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {project.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">My Tasks</h2>
        </div>

        {tasks.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle2 className="mx-auto text-gray-400" size={48} />
            <p className="text-gray-600 mt-4">No tasks assigned</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{task.title}</h3>
                  <Link
                    to={`/projects/${task.project_id}`}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    View project →
                  </Link>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    task.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : task.status === 'in_progress'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {task.status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

