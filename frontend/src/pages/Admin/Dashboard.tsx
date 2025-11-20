import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminAPI } from '../../services/api';
import { Button } from '../../components/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card';
import { Input } from '../../components/Input';
import { Select } from '../../components/Select';

export const AdminDashboard: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [crawlingIds, setCrawlingIds] = useState<Set<number>>(new Set());
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    frequency_hours: 24,
    enabled: true,
  });
  const queryClient = useQueryClient();

  const { data: origins, isLoading } = useQuery({
    queryKey: ['origins'],
    queryFn: adminAPI.getOrigins,
  });

  const createMutation = useMutation({
    mutationFn: adminAPI.createOrigin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      setShowForm(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => adminAPI.updateOrigin(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      setEditingId(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: adminAPI.deleteOrigin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
    },
  });

  const crawlMutation = useMutation({
    mutationFn: adminAPI.triggerCrawl,
    onSuccess: (data, originId) => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      setCrawlingIds(prev => {
        const next = new Set(prev);
        next.delete(originId);
        return next;
      });
      // Show success message
      if (data.success) {
        alert(`Crawl successful: ${data.message}`);
      } else {
        alert(`Crawl failed: ${data.message}`);
      }
    },
    onError: (error: any, originId) => {
      setCrawlingIds(prev => {
        const next = new Set(prev);
        next.delete(originId);
        return next;
      });
      alert(`Crawl error: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      url: '',
      frequency_hours: 24,
      enabled: true,
    });
  };

  const handleEdit = (origin: any) => {
    setEditingId(origin.id);
    setFormData({
      name: origin.name,
      url: origin.url,
      frequency_hours: origin.frequency_hours,
      enabled: origin.enabled,
    });
    setShowForm(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    resetForm();
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this origin?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleToggle = (origin: any) => {
    updateMutation.mutate({
      id: origin.id,
      data: { enabled: !origin.enabled },
    });
  };

  const handleCrawl = (origin: any) => {
    if (crawlingIds.has(origin.id)) return; // Prevent double-click
    
    setCrawlingIds(prev => new Set(prev).add(origin.id));
    crawlMutation.mutate(origin.id);
  };

  const getStatusBadge = (status: string | null) => {
    if (!status) return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">Never Run</span>;
    if (status.toLowerCase().startsWith('success')) {
      return <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-700">Success</span>;
    }
    if (status.toLowerCase().startsWith('failed')) {
      return <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-700">Failed</span>;
    }
    return <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-700">{status}</span>;
  };

  const getQdrantStatusBadge = (qdrantStatus: string | null) => {
    if (!qdrantStatus) {
      return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700" title="Qdrant status unknown">Not Synced</span>;
    }
    if (qdrantStatus.toLowerCase().startsWith('success')) {
      return <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-700" title="Document synced to Qdrant">Synced</span>;
    }
    if (qdrantStatus.toLowerCase().startsWith('failed')) {
      const errorMsg = qdrantStatus.includes(':') ? qdrantStatus.split(':')[1].trim() : 'Qdrant error';
      return (
        <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-700" title={`Qdrant error: ${errorMsg}`}>
          Qdrant Error
        </span>
      );
    }
    return <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-700">{qdrantStatus}</span>;
  };

  const parseCrawlStatus = (lastStatus: string | null) => {
    if (!lastStatus) return { status: 'never', error: null };
    if (lastStatus.toLowerCase().startsWith('crawl: success')) {
      return { status: 'success', error: null };
    }
    if (lastStatus.toLowerCase().startsWith('crawl: failed')) {
      const parts = lastStatus.split(',');
      const crawlPart = parts.find(p => p.toLowerCase().startsWith('crawl:'));
      const error = crawlPart ? crawlPart.replace(/^crawl:\s*failed:?\s*/i, '').trim() : 'Unknown error';
      return { status: 'failed', error };
    }
    return { status: 'unknown', error: null };
  };

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-secondary-900">Admin Dashboard</h1>
            <p className="text-secondary-600 mt-2">Manage scraping origins and system configuration</p>
          </div>
          <Button onClick={() => setShowForm(true)} disabled={showForm}>
            Add Origin
          </Button>
        </div>

        {showForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{editingId ? 'Edit Origin' : 'Add New Origin'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
                <Input
                  label="URL"
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  required
                />
                <Input
                  label="Frequency (hours)"
                  type="number"
                  value={formData.frequency_hours}
                  onChange={(e) => setFormData({ ...formData, frequency_hours: parseInt(e.target.value) })}
                  min={1}
                  required
                />
                <Select
                  label="Status"
                  value={formData.enabled ? 'enabled' : 'disabled'}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.value === 'enabled' })}
                  options={[
                    { value: 'enabled', label: 'Enabled' },
                    { value: 'disabled', label: 'Disabled' },
                  ]}
                />
                <div className="flex gap-4">
                  <Button type="submit">
                    {editingId ? 'Update' : 'Create'}
                  </Button>
                  <Button type="button" variant="secondary" onClick={handleCancel}>
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="text-center py-12">
            <p className="text-secondary-600">Loading...</p>
          </div>
        ) : origins && origins.length > 0 ? (
          <div className="grid gap-4">
            {origins.map((origin: any) => (
              <Card key={origin.id} hover>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-secondary-900 mb-2">
                      {origin.name}
                    </h3>
                    <p className="text-secondary-600 mb-2">
                      <a href={origin.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                        {origin.url}
                      </a>
                    </p>
                    <div className="flex gap-4 text-sm text-secondary-500 items-center flex-wrap">
                      <span>Frequency: {origin.frequency_hours}h</span>
                      <span>Last run: {origin.last_run ? new Date(origin.last_run).toLocaleString() : 'Never'}</span>
                    </div>
                    <div className="flex gap-2 items-center mt-2">
                      <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-600 font-medium">Crawl:</span>
                        {getStatusBadge(parseCrawlStatus(origin.last_status).status === 'success' ? 'success' : parseCrawlStatus(origin.last_status).status === 'failed' ? 'failed' : origin.last_status)}
                      </div>
                      <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-600 font-medium">Qdrant:</span>
                        {getQdrantStatusBadge(origin.qdrant_status)}
                      </div>
                    </div>
                    {parseCrawlStatus(origin.last_status).error && (
                      <div className="mt-2 text-xs text-red-600">
                        <strong>Crawl Error:</strong> {parseCrawlStatus(origin.last_status).error}
                      </div>
                    )}
                    {origin.qdrant_status && origin.qdrant_status.toLowerCase().startsWith('failed') && (
                      <div className="mt-2 text-xs text-red-600">
                        <strong>Qdrant Error:</strong> {origin.qdrant_status.includes(':') ? origin.qdrant_status.split(':').slice(1).join(':').trim() : origin.qdrant_status.replace(/^failed:?\s*/i, '')}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleCrawl(origin)}
                      disabled={crawlingIds.has(origin.id) || !origin.enabled}
                    >
                      {crawlingIds.has(origin.id) ? 'Crawling...' : 'Crawl Now'}
                    </Button>
                    <Button
                      variant={origin.enabled ? 'secondary' : 'primary'}
                      size="sm"
                      onClick={() => handleToggle(origin)}
                    >
                      {origin.enabled ? 'Disable' : 'Enable'}
                    </Button>
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() => handleEdit(origin)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(origin.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent>
              <p className="text-secondary-600 text-center py-8">
                No origins configured. Add your first origin to get started.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

