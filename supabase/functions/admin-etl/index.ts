import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Extract auth token
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response('Unauthorized', { 
        status: 401, 
        headers: corsHeaders 
      })
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // For now, we'll simulate ETL triggers
    // In a real implementation, these would trigger actual ETL processes
    const url = new URL(req.url)
    const etlType = url.pathname.split('/').pop()

    let result = { success: false, message: 'Unknown ETL type' }

    switch (etlType) {
      case 'ctgov':
        // Simulate ClinicalTrials.gov ETL
        result = {
          success: true,
          message: 'ClinicalTrials.gov ETL triggered successfully',
          timestamp: new Date().toISOString()
        }
        break
        
      case 'fda':
        // Simulate FDA approvals ETL
        result = {
          success: true,
          message: 'FDA approvals ETL triggered successfully',
          timestamp: new Date().toISOString()
        }
        break
        
      case 'edgar':
        // Simulate EDGAR filings ETL
        result = {
          success: true,
          message: 'EDGAR filings ETL triggered successfully',
          timestamp: new Date().toISOString()
        }
        break
        
      case 'refresh-search':
        // Refresh search materialized view
        const { error } = await supabaseClient.rpc('refresh_search_mv')
        if (error) {
          result = {
            success: false,
            message: `Failed to refresh search view: ${error.message}`
          }
        } else {
          result = {
            success: true,
            message: 'Search materialized view refreshed successfully',
            timestamp: new Date().toISOString()
          }
        }
        break
        
      default:
        result = {
          success: false,
          message: `Unknown ETL type: ${etlType}. Available: ctgov, fda, edgar, refresh-search`
        }
    }

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (error) {
    console.error('Admin ETL error:', error)
    return new Response(JSON.stringify({ 
      success: false, 
      error: 'Internal server error' 
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})