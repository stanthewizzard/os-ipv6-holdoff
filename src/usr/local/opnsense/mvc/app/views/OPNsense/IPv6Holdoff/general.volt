<script>
$(function() {
    mapDataToFormUI({'frm_general_settings':'/api/ipv6holdoff/settings/get'}).done(function(){formatTokenizersUI();$('.selectpicker').selectpicker('refresh');});
    $('#save').click(function(){saveFormToEndpoint('/api/ipv6holdoff/settings/set','frm_general_settings',function(){ajaxCall('/api/ipv6holdoff/service/reconfigure',{},function(){refresh();});});});
    function refresh(){ajaxGet('/api/ipv6holdoff/service/status',{},function(data){$('#status').text(JSON.stringify(data,null,2));});}
    refresh(); setInterval(refresh,5000);
});
</script>
<div class="alert alert-info">IPv4/CARP remain immediate. Public IPv6 on the standby node waits for the configured delay. Observation mode never changes router advertisements or interface addresses.</div>
{{ partial("layout_partials/base_form",['fields':generalForm,'id':'frm_general_settings']) }}
<div class="col-md-12"><button class="btn btn-primary" id="save" type="button">{{ lang._('Save and apply') }}</button><h3>{{ lang._('Status') }}</h3><pre id="status"></pre></div>
