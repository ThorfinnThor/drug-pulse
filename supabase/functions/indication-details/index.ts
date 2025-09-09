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
    const url = new URL(req.url)
    const indicationId = url.searchParams.get('id')
    
    if (!indicationId) {
      return new Response(JSON.stringify({ error: 'Missing indication ID' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Get indication details
    const { data: indication, error: indicationError } = await supabaseClient
      .from('indications')
      .select('*')
      .eq('id', indicationId)
      .single()

    if (indicationError) {
      return new Response(JSON.stringify({ error: indicationError.message }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      })
    }

    // Get trial funnel data
    const { data: funnelData, error: funnelError } = await supabaseClient
      .from('v_trial_funnel_by_indication')
      .select('*')
      .eq('indication_id', indicationId)

    // Get late-stage trials
    const { data: lateStageTrials, error: trialsError } = await supabaseClient
      .from('trials')
      .select(`
        id,
        title,
        phase,
        status,
        primary_completion_date,
        companies!sponsor_company_id(canonical_name)
      `)
      .in('phase', ['2/3', '3'])
      .gte('primary_completion_date', new Date().toISOString().split('T')[0])
      .eq('trial_indications.indication_id', indicationId)

    const result = {
      indication: {
        id: indication.id,
        label: indication.label,
        description: indication.description,
        mesh_id: indication.mesh_id,
        icd10: indication.icd10
      },
      funnel: funnelData?.map(item => ({
        phase: item.phase,
        n: item.trial_count
      })) || [],
      late_stage_trials: lateStageTrials?.map(trial => ({
        trial_id: trial.id,
        title: trial.title,
        phase: trial.phase,
        status: trial.status,
        primary_completion_date: trial.primary_completion_date,
        sponsor: trial.companies?.canonical_name
      })) || []
    }

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })

  } catch (error) {
    console.error('Function error:', error)
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
  }
})