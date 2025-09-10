import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Play, CheckCircle, XCircle, Clock, Shield } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";

interface ETLExecution {
  id: string;
  etl_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

const AdminPage = () => {
  const [user, setUser] = useState<any>(null);
  const [isOwner, setIsOwner] = useState(false);
  const [loading, setLoading] = useState(true);
  const [executions, setExecutions] = useState<ETLExecution[]>([]);
  const [runningETL, setRunningETL] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        navigate('/auth');
        return;
      }

      setUser(session.user);

      // Check if user has owner role
      const { data: roles, error } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', session.user.id)
        .eq('role', 'owner');

      if (error) {
        console.error('Error checking roles:', error);
        toast({
          title: "Error",
          description: "Failed to check user permissions",
          variant: "destructive",
        });
        return;
      }

      if (!roles || roles.length === 0) {
        toast({
          title: "Access Denied",
          description: "Owner access required for admin dashboard",
          variant: "destructive",
        });
        navigate('/');
        return;
      }

      setIsOwner(true);
      await fetchETLHistory();
      
    } catch (error) {
      console.error('Auth check error:', error);
      navigate('/auth');
    } finally {
      setLoading(false);
    }
  };

  const fetchETLHistory = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const response = await fetch('/api/admin/etl-history', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setExecutions(data.executions || []);
      }
    } catch (error) {
      console.error('Error fetching ETL history:', error);
    }
  };

  const runETL = async (etlType: string) => {
    try {
      setRunningETL(etlType);
      
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('No session');
      }

      const response = await fetch(`/api/admin/run/${etlType}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (response.ok) {
        toast({
          title: "ETL Started",
          description: result.message,
        });
        await fetchETLHistory();
      } else {
        throw new Error(result.detail || 'ETL failed');
      }
      
    } catch (error) {
      console.error('ETL error:', error);
      toast({
        title: "ETL Failed",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive",
      });
    } finally {
      setRunningETL(null);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    );
  }

  if (!isOwner) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Access denied. Owner privileges required to access admin dashboard.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage ETL processes and data ingestion</p>
        </div>
        <Badge variant="secondary" className="flex items-center gap-1">
          <Shield className="h-3 w-3" />
          Owner Access
        </Badge>
      </div>

      {/* ETL Control Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              ClinicalTrials.gov ETL
            </CardTitle>
            <CardDescription>
              Fetch recent clinical trials data from ClinicalTrials.gov API
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runETL('ctgov')}
              disabled={runningETL === 'ctgov'}
              className="w-full"
            >
              {runningETL === 'ctgov' ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                'Run CTGov ETL'
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              FDA Approvals ETL
            </CardTitle>
            <CardDescription>
              Fetch recent drug approvals from openFDA API
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runETL('fda')}
              disabled={runningETL === 'fda'}
              className="w-full"
            >
              {runningETL === 'fda' ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                'Run FDA ETL'
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              EDGAR Filings ETL
            </CardTitle>
            <CardDescription>
              Fetch recent SEC filings for tracked companies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runETL('edgar')}
              disabled={runningETL === 'edgar'}
              className="w-full"
            >
              {runningETL === 'edgar' ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                'Run EDGAR ETL'
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* ETL History */}
      <Card>
        <CardHeader>
          <CardTitle>Recent ETL Executions</CardTitle>
          <CardDescription>
            History of ETL runs and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {executions.length === 0 ? (
            <p className="text-muted-foreground">No ETL executions found</p>
          ) : (
            <div className="space-y-2">
              {executions.map((execution) => (
                <div key={execution.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(execution.status)}
                    <div>
                      <p className="font-medium capitalize">{execution.etl_type} ETL</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(execution.started_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={getStatusColor(execution.status)}>
                      {execution.status}
                    </Badge>
                    {execution.error_message && (
                      <Badge variant="outline" className="text-xs max-w-xs truncate">
                        {execution.error_message}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminPage;