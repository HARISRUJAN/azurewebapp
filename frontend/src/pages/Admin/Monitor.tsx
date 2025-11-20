import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminAPI } from '../../services/api';
import { Button } from '../../components/Button';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card';
import { Alert } from '../../components/Alert';

export const Monitor: React.FC = () => {
  const [crawlingIds, setCrawlingIds] = useState<Set<number>>(new Set());
  const [expandedErrors, setExpandedErrors] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();

  // Fetch origins with auto-refresh every 30 seconds
  const { data: origins, isLoading: originsLoading, dataUpdatedAt } = useQuery({
    queryKey: ['origins'],
    queryFn: adminAPI.getOrigins,
    refetchInterval: 30000, // 30 seconds
  });

  // Fetch health status
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: adminAPI.getHealth,
    refetchInterval: 30000,
  });

  const crawlMutation = useMutation({
    mutationFn: adminAPI.triggerCrawl,
    onSuccess: (_data, originId) => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
      setCrawlingIds(prev => {
        const next = new Set(prev);
        next.delete(originId);
        return next;
      });
    },
    onError: (_error: any, originId) => {
      setCrawlingIds(prev => {
        const next = new Set(prev);
        next.delete(originId);
        return next;
      });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      adminAPI.updateOrigin(id, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['origins'] });
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
  });

  // Calculate statistics
  const stats = useMemo(() => {
    if (!origins) return null;

    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const total = origins.length;
    const enabled = origins.filter((o: any) => o.enabled).length;
    const successful = origins.filter((o: any) => {
      if (!o.last_run) return false;
      const lastRun = new Date(o.last_run);
      return lastRun >= last24h && o.last_status?.toLowerCase().startsWith('success');
    }).length;
    const failed = origins.filter((o: any) => {
      if (!o.last_run) return false;
      const lastRun = new Date(o.last_run);
      return lastRun >= last24h && o.last_status?.toLowerCase().startsWith('failed');
    }).length;

    return { total, enabled, successful, failed };
  }, [origins]);

  // Activity feed (recent crawls)
  const activityFeed = useMemo(() => {
    if (!origins) return [];
    
    return origins
      .filter((o: any) => o.last_run)
      .map((o: any) => ({
        id: o.id,
        name: o.name,
        timestamp: new Date(o.last_run),
        status: o.last_status,
        enabled: o.enabled,
      }))
      .sort((a: { timestamp: Date }, b: { timestamp: Date }) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, 20);
  }, [origins]);

  const handleCrawl = (origin: any) => {
    if (crawlingIds.has(origin.id) || !origin.enabled) return;
    
    setCrawlingIds(prev => new Set(prev).add(origin.id));
    crawlMutation.mutate(origin.id);
  };

  const handleToggle = (origin: any) => {
    toggleMutation.mutate({
      id: origin.id,
      enabled: !origin.enabled,
    });
  };

  const toggleErrorExpansion = (id: number) => {
    setExpandedErrors(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getStatusBadge = (status: string | null) => {
    if (!status) {
      return <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700">Never Run</span>;
    }
    if (status.toLowerCase().startsWith('success')) {
      return <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">Success</span>;
    }
    if (status.toLowerCase().startsWith('failed')) {
      return <span className="px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-800">Failed</span>;
    }
    return <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-800">{status}</span>;
  };

  const getQdrantStatusBadge = (qdrantStatus: string | null) => {
    if (!qdrantStatus) {
      return <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700" title="Qdrant status unknown">Not Synced</span>;
    }
    if (qdrantStatus.toLowerCase().startsWith('success')) {
      return <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800" title="Document synced to Qdrant">Synced</span>;
    }
    if (qdrantStatus.toLowerCase().startsWith('failed')) {
      const errorMsg = qdrantStatus.includes(':') ? qdrantStatus.split(':')[1].trim() : 'Qdrant error';
      return (
        <span className="px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-800" title={`Qdrant error: ${errorMsg}`}>
          Qdrant Error
        </span>
      );
    }
    return <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-800">{qdrantStatus}</span>;
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

  const getRelativeTime = (date: Date | string | null) => {
    if (!date) return 'Never';
    const d = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString();
  };

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['origins'] });
    queryClient.invalidateQueries({ queryKey: ['health'] });
  };

  if (originsLoading || healthLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-secondary-600">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-secondary-900">System Monitor</h1>
            <p className="text-secondary-600 mt-2">Real-time monitoring and activity dashboard</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-secondary-500">
              Last updated: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : 'Never'}
            </div>
            <Button variant="secondary" size="sm" onClick={handleRefresh}>
              Refresh
            </Button>
          </div>
        </div>

        {/* System Status Alert */}
        <div className="mb-6">
          <Alert variant={health?.status === 'healthy' ? 'success' : 'warning'}>
            System Status: <strong>{health?.status || 'Unknown'}</strong>
            {health?.status === 'healthy' && ' - All systems operational'}
          </Alert>
        </div>

        {/* System Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <Card>
            <CardContent>
              <div className="text-sm text-secondary-600 mb-1">Total Origins</div>
              <div className="text-3xl font-bold text-secondary-900">{stats?.total || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-sm text-secondary-600 mb-1">Enabled</div>
              <div className="text-3xl font-bold text-primary-600">{stats?.enabled || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-sm text-secondary-600 mb-1">Successful (24h)</div>
              <div className="text-3xl font-bold text-green-600">{stats?.successful || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-sm text-secondary-600 mb-1">Failed (24h)</div>
              <div className="text-3xl font-bold text-red-600">{stats?.failed || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <div className="text-sm text-secondary-600 mb-1">Disabled</div>
              <div className="text-3xl font-bold text-gray-600">
                {(stats?.total || 0) - (stats?.enabled || 0)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Origin Monitoring Table */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Origin Monitoring</CardTitle>
          </CardHeader>
          <CardContent>
            {origins && origins.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-secondary-200">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Name</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">URL</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Last Run</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Crawl Status</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Qdrant Status</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Frequency</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {origins.map((origin: any) => (
                      <tr key={origin.id} className="border-b border-secondary-100 hover:bg-secondary-50">
                        <td className="py-3 px-4">
                          <div className="font-medium text-secondary-900">{origin.name}</div>
                        </td>
                        <td className="py-3 px-4">
                          <a
                            href={origin.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:underline text-sm truncate max-w-xs block"
                            title={origin.url}
                          >
                            {origin.url}
                          </a>
                        </td>
                        <td className="py-3 px-4">
                          {origin.enabled ? (
                            <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-800">
                              Enabled
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700">
                              Disabled
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-secondary-600">
                          {origin.last_run ? (
                            <div>
                              <div>{getRelativeTime(origin.last_run)}</div>
                              <div className="text-xs text-secondary-500">
                                {new Date(origin.last_run).toLocaleString()}
                              </div>
                            </div>
                          ) : (
                            'Never'
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-col gap-1">
                            {getStatusBadge(parseCrawlStatus(origin.last_status).status === 'success' ? 'success' : parseCrawlStatus(origin.last_status).status === 'failed' ? 'failed' : origin.last_status)}
                            {parseCrawlStatus(origin.last_status).error && (
                              <button
                                onClick={() => toggleErrorExpansion(origin.id)}
                                className="text-xs text-red-600 hover:underline text-left"
                              >
                                {expandedErrors.has(origin.id) ? 'Hide' : 'Show'} crawl error
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-col gap-1">
                            {getQdrantStatusBadge(origin.qdrant_status)}
                            {origin.qdrant_status && origin.qdrant_status.toLowerCase().startsWith('failed') && (
                              <button
                                onClick={() => toggleErrorExpansion(origin.id)}
                                className="text-xs text-red-600 hover:underline text-left"
                              >
                                {expandedErrors.has(origin.id) ? 'Hide' : 'Show'} qdrant error
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-secondary-600">
                          {origin.frequency_hours}h
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2">
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleCrawl(origin)}
                              disabled={crawlingIds.has(origin.id) || !origin.enabled}
                              title={!origin.enabled ? 'Enable origin first' : 'Trigger crawl now'}
                            >
                              {crawlingIds.has(origin.id) ? 'Crawling...' : 'Crawl'}
                            </Button>
                            <Button
                              variant={origin.enabled ? 'secondary' : 'primary'}
                              size="sm"
                              onClick={() => handleToggle(origin)}
                            >
                              {origin.enabled ? 'Disable' : 'Enable'}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-secondary-600">
                No origins configured. Add origins in the Dashboard to start monitoring.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Error Details (expanded) */}
        {origins && origins.some((o: any) => 
          expandedErrors.has(o.id) && (parseCrawlStatus(o.last_status).error || (o.qdrant_status && o.qdrant_status.toLowerCase().startsWith('failed')))
        ) && (
          <div className="mb-8">
            {origins
              .filter((o: any) => expandedErrors.has(o.id) && (parseCrawlStatus(o.last_status).error || (o.qdrant_status && o.qdrant_status.toLowerCase().startsWith('failed'))))
              .map((origin: any) => (
                <Card key={origin.id} className="mb-4 border-red-200 bg-red-50">
                  <CardHeader>
                    <CardTitle className="text-red-900">Error Details: {origin.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {parseCrawlStatus(origin.last_status).error && (
                      <div className="mb-4">
                        <div className="text-sm font-semibold text-red-900 mb-1">Crawl Error:</div>
                        <div className="text-sm text-red-800 font-mono whitespace-pre-wrap">
                          {parseCrawlStatus(origin.last_status).error}
                        </div>
                      </div>
                    )}
                    {origin.qdrant_status && origin.qdrant_status.toLowerCase().startsWith('failed') && (
                      <div className="mb-4">
                        <div className="text-sm font-semibold text-red-900 mb-1">Qdrant Error:</div>
                        <div className="text-sm text-red-800 font-mono whitespace-pre-wrap">
                          {origin.qdrant_status.includes(':') ? origin.qdrant_status.split(':').slice(1).join(':').trim() : origin.qdrant_status.replace(/^failed:?\s*/i, '')}
                        </div>
                      </div>
                    )}
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() => toggleErrorExpansion(origin.id)}
                      className="mt-2"
                    >
                      Hide Details
                    </Button>
                  </CardContent>
                </Card>
              ))}
          </div>
        )}

        {/* Activity Feed */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {activityFeed.length > 0 ? (
              <div className="space-y-3">
                {activityFeed.map((activity: { id: number; name: string; timestamp: Date; status: string | null; enabled: boolean }) => (
                  <div
                    key={`${activity.id}-${activity.timestamp.getTime()}`}
                    className="flex items-center justify-between py-2 px-3 rounded border border-secondary-200 bg-white"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <div className="flex-shrink-0">
                        {getStatusBadge(activity.status)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-secondary-900 truncate">
                          {activity.name}
                        </div>
                        <div className="text-xs text-secondary-500">
                          {activity.timestamp.toLocaleString()}
                        </div>
                      </div>
                      <div className="text-sm text-secondary-600">
                        {getRelativeTime(activity.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-secondary-600">
                No crawl activity yet. Trigger a crawl to see activity here.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

