import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { GraduationCap, Users, FolderKanban, CheckCircle2, TrendingUp } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface DashboardStats {
  total_projects: number;
  active_projects: number;
  total_students: number;
  total_professors: number;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  recent_projects: Array<{
    id: number;
    title: string;
    created_at: string;
  }>;
}

interface ProjectAnalytics {
  project_id: number;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  total_hours: number;
  member_contributions: Array<{
    user_id: number;
    user_name: string;
    tasks_assigned: number;
    tasks_completed: number;
    hours_spent: number;
  }>;
  skill_distribution: Record<string, number>;
}

export default function ProfessorDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [analytics, setAnalytics] = useState<ProjectAnalytics[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, projectsRes] = await Promise.all([
        api.get('/api/analytics/dashboard'),
        api.get('/api/projects/'),
      ]);

      setStats(statsRes.data);

      // Fetch analytics for first 5 projects
      const projectAnalytics = await Promise.all(
        projectsRes.data.slice(0, 5).map((project: any) =>
          api
            .get(`/api/analytics/project/${project.id}`)
            .then((res) => res.data)
            .catch(() => null)
        )
      );
      setAnalytics(projectAnalytics.filter(Boolean));
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!stats) {
    return <div>Failed to load dashboard</div>;
  }

  const completionData = [
    { name: 'Completed', value: stats.completed_tasks },
    { name: 'In Progress', value: stats.total_tasks - stats.completed_tasks },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Professor Dashboard</h1>
        <p className="text-gray-600 mt-2">Overview of all academic projects and students</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Projects</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total_projects}</p>
              <p className="text-xs text-green-600 mt-1">
                {stats.active_projects} active
              </p>
            </div>
            <FolderKanban className="text-primary-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Students</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total_students}</p>
            </div>
            <Users className="text-blue-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Tasks</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total_tasks}</p>
              <p className="text-xs text-green-600 mt-1">
                {stats.completed_tasks} completed
              </p>
            </div>
            <CheckCircle2 className="text-green-600" size={32} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Completion Rate</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">
                {stats.completion_rate.toFixed(1)}%
              </p>
            </div>
            <TrendingUp className="text-purple-600" size={32} />
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Task Completion Chart */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Task Completion</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={completionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {completionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Project Activity */}
        {analytics.length > 0 && (
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Project Activity</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.slice(0, 5)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="project_id" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="completed_tasks" fill="#10b981" name="Completed" />
                <Bar dataKey="in_progress_tasks" fill="#0ea5e9" name="In Progress" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent Projects */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Recent Projects</h2>
        {stats.recent_projects.length === 0 ? (
          <p className="text-gray-600">No projects yet</p>
        ) : (
          <div className="space-y-3">
            {stats.recent_projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="block p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
              >
                <h3 className="font-semibold text-gray-900">{project.title}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Created: {new Date(project.created_at).toLocaleDateString()}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

