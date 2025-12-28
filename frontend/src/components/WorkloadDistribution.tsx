import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface WorkloadDistributionProps {
  projectId: number;
}

interface MemberWorkload {
  user_id: number;
  user_name: string;
  tasks_assigned: number;
  tasks_completed: number;
  hours_spent: number;
  hours_estimated: number;
}

export default function WorkloadDistribution({ projectId }: WorkloadDistributionProps) {
  const [workload, setWorkload] = useState<MemberWorkload[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWorkload();
  }, [projectId]);

  const fetchWorkload = async () => {
    try {
      const response = await api.get(`/api/analytics/project/${projectId}`);
      setWorkload(response.data.member_contributions || []);
    } catch (error) {
      console.error('Failed to fetch workload:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (workload.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-600">No workload data available</p>
      </div>
    );
  }

  const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  // Calculate workload balance
  const totalHours = workload.reduce((sum, m) => sum + m.hours_spent, 0);
  const avgHours = totalHours / workload.length;
  const workloadBalance = workload.map(m => ({
    ...m,
    balance_ratio: avgHours > 0 ? (m.hours_spent / avgHours) : 0,
  }));

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Workload Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={workload}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="user_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="hours_spent" fill="#0ea5e9" name="Hours Spent" />
            <Bar dataKey="tasks_assigned" fill="#10b981" name="Tasks Assigned" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Task Completion</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={workload.map(m => ({
                  name: m.user_name,
                  value: m.tasks_completed,
                }))}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {workload.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Workload Balance</h3>
          <div className="space-y-3">
            {workloadBalance.map((member) => (
              <div key={member.user_id}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-gray-700">{member.user_name}</span>
                  <span className="text-sm text-gray-600">
                    {member.balance_ratio.toFixed(1)}x avg
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      member.balance_ratio > 1.2
                        ? 'bg-red-500'
                        : member.balance_ratio < 0.8
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(member.balance_ratio * 50, 100)}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {member.hours_spent}h / {member.tasks_assigned} tasks
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Member Contributions</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tasks Assigned
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tasks Completed
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hours Spent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Completion Rate
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {workload.map((member) => (
                <tr key={member.user_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {member.user_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {member.tasks_assigned}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {member.tasks_completed}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {member.hours_spent.toFixed(1)}h
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {member.tasks_assigned > 0
                      ? ((member.tasks_completed / member.tasks_assigned) * 100).toFixed(0)
                      : 0}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

