import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminAPI } from '../../services/api';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/Card';
import { Alert } from '../../components/Alert';

export const Health: React.FC = () => {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: adminAPI.getHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-secondary-50 p-8">
        <div className="max-w-6xl mx-auto">
          <p className="text-secondary-600">Loading health status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-secondary-900 mb-8">System Health</h1>

        <div className="mb-6">
          <Alert variant={health?.status === 'healthy' ? 'success' : 'warning'}>
            System Status: {health?.status || 'Unknown'}
          </Alert>
        </div>

        <div className="grid gap-4">
          {health?.origins && health.origins.length > 0 ? (
            health.origins.map((origin: any) => (
              <Card key={origin.origin_id}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>{origin.origin_name}</CardTitle>
                    <div className="flex items-center gap-2">
                      {origin.enabled ? (
                        <span className="px-2 py-1 bg-success-100 text-success-800 text-sm rounded">
                          Enabled
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-secondary-100 text-secondary-800 text-sm rounded">
                          Disabled
                        </span>
                      )}
                      {origin.last_status === 'success' && (
                        <span className="px-2 py-1 bg-success-100 text-success-800 text-sm rounded">
                          ✓ Success
                        </span>
                      )}
                      {origin.last_status === 'failed' && (
                        <span className="px-2 py-1 bg-error-100 text-error-800 text-sm rounded">
                          ✗ Failed
                        </span>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <p>
                      <span className="font-medium">Last Run:</span>{' '}
                      {origin.last_run ? new Date(origin.last_run).toLocaleString() : 'Never'}
                    </p>
                    <p>
                      <span className="font-medium">Last Status:</span>{' '}
                      {origin.last_status || 'N/A'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent>
                <p className="text-secondary-600 text-center py-8">
                  No origins configured.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

