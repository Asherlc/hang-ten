"""Prospective muted-workflow scalar gates; no runtime actions."""
AUDIO_SNAPSHOT_EVENTS = ('startup-audio-preparation-change', 'startup-deferred-dispatch', 'startup-request-entry', 'startup-request-deferred', 'startup-audio-arm-before', 'startup-audio-arm-after', 'startup-arm-task-enter', 'startup-arm-task-cancelled', 'startup-arm-task-resumed', 'startup-visible-countdown-before', 'startup-visible-countdown-after', 'startup-audio-prepare-before', 'startup-audio-prepare-after')
FORBIDDEN_PREPARE_EVENTS = ('startup-audio-prepare-before', 'startup-audio-prepare-after')
def validate(rows, final=False):
    snapshots=[]
    for r in rows:
        event=r.get('event','')
        assert event not in FORBIDDEN_PREPARE_EVENTS, 'Muted workflow entered countdown audio preparation'
        if event in AUDIO_SNAPSHOT_EVENTS or (event.startswith('startup-') and 'audioEnabled' in r):
            assert r.get('audioEnabled') is False, 'Startup audioEnabled is not explicit false at '+event
            snapshots.append(dict(sequence=r['sequence'],event=event,audioEnabled=r['audioEnabled']))
    if final:
        assert snapshots, 'No startup audio snapshots captured'
        for required in ('startup-request-entry','startup-visible-countdown-before','startup-visible-countdown-after'):
            assert any(r['event']==required for r in snapshots), 'Missing muted startup boundary '+required
    return dict(audioMuted=True, snapshots=snapshots, noPrepareEvents=True, finalRequirementsChecked=final, limitation='Sampled scalar settings and call boundaries; not proof of all framework audio inactivity.')
