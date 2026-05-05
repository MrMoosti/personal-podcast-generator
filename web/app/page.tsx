'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Types ────────────────────────────────────────────────────────────────────

const DURATIONS = [5, 10, 15, 20] as const;
type Duration = (typeof DURATIONS)[number];

type StageId = 'researching' | 'writing' | 'synthesizing' | 'assembling' | 'done' | 'error' | 'ping';
interface SseEvent   { stage: StageId; message: string }
interface ScriptLine { speaker: string; text: string; segment: string }
interface Script     { topic: string; duration_minutes: number; lines: ScriptLine[]; speaker_names?: Record<string, string> }

const ALL_STAGES: StageId[]   = ['researching', 'writing', 'synthesizing', 'assembling'];
const REGEN_STAGES: StageId[] = ['synthesizing', 'assembling'];
const STAGE_LABELS: Record<string, string> = {
  researching: 'Researching topic',
  writing:     'Writing script',
  synthesizing:'Synthesizing audio',
  assembling:  'Assembling podcast',
};

// ── Voice helpers ─────────────────────────────────────────────────────────────

const VOICE_NAMES: Record<string, string> = {
  am_michael: 'Michael', am_adam:    'Adam',
  af_bella:   'Bella',   af_nicole:  'Nicole',  af_sarah:   'Sarah',
  bf_emma:    'Emma',    bf_isabella:'Isabella',
  bm_george:  'George',  bm_lewis:   'Lewis',
};

const voiceName  = (id: string) => VOICE_NAMES[id] ?? id.split('_').pop() ?? id;
const speakerBadgeClass = (speakerId: string) => {
  if (speakerId === 'host') return 'bg-blue-900 text-blue-300';
  const idx = parseInt(speakerId.replace('expert_', ''), 10) || 0;
  return (['bg-purple-900 text-purple-300', 'bg-green-900 text-green-300', 'bg-amber-900 text-amber-300'])[idx % 3];
};

// ── Misc helpers ──────────────────────────────────────────────────────────────

const slugify = (text: string) =>
  text.toLowerCase().trim()
    .replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-')
    .slice(0, 60).replace(/^-+|-+$/g, '');

const DEFAULT_VOICES: Record<string, string> = {
  am_michael: 'Michael (American male)',   am_adam:    'Adam (American male)',
  af_bella:   'Bella (American female)',   af_nicole:  'Nicole (American female)',
  af_sarah:   'Sarah (American female)',
  bf_emma:    'Emma (British female)',     bf_isabella:'Isabella (British female)',
  bm_george:  'George (British male)',     bm_lewis:   'Lewis (British male)',
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function Home() {
  // Form
  const [topic, setTopic]       = useState('');
  const [duration, setDuration] = useState<Duration>(10);

  // Voice config
  const [voiceOptions, setVoiceOptions] = useState<Record<string, string>>(DEFAULT_VOICES);
  const [hostVoice, setHostVoice]       = useState('am_michael');
  const [expertVoices, setExpertVoices] = useState<string[]>(['bf_emma']);
  const [voicesOpen, setVoicesOpen]     = useState(false);

  // Voice preview
  const previewRef         = useRef<HTMLAudioElement | null>(null);
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);

  // Job / streaming
  const [phase, setPhase]     = useState<'idle' | 'generating' | 'done' | 'error'>('idle');
  const [isRegen, setIsRegen] = useState(false);
  const [events, setEvents]   = useState<SseEvent[]>([]);
  const [jobId, setJobId]     = useState<string | null>(null);
  const [script, setScript]   = useState<Script | null>(null);
  const [scriptOpen, setScriptOpen] = useState(false);
  const [errorMsg, setErrorMsg]     = useState('');
  const esRef   = useRef<EventSource | null>(null);
  const doneRef = useRef(false);

  // Fetch available voices on mount
  useEffect(() => {
    fetch(`${API}/api/voices`)
      .then((r) => r.json())
      .then((data: Record<string, string>) => setVoiceOptions(data))
      .catch(() => {});
  }, []);

  // ── Voice helpers ─────────────────────────────────────────────────────────

  /** All voices already chosen by other personas — passed to a select to disable them. */
  const usedBy = useCallback((persona: 'host' | number): Set<string> => {
    const used = new Set<string>();
    if (persona !== 'host') used.add(hostVoice);
    expertVoices.forEach((v, i) => { if (i !== persona) used.add(v); });
    return used;
  }, [hostVoice, expertVoices]);

  /** Pick the first voice not currently in use. */
  const unusedVoice = useCallback((): string => {
    const used = new Set([hostVoice, ...expertVoices]);
    return Object.keys(voiceOptions).find((v) => !used.has(v))
        ?? Object.keys(voiceOptions)[0]
        ?? 'bm_george';
  }, [hostVoice, expertVoices, voiceOptions]);

  const addExpert    = () => setExpertVoices((p) => [...p, unusedVoice()]);
  const removeExpert = (i: number) => setExpertVoices((p) => p.filter((_, j) => j !== i));
  const changeExpert = (i: number, v: string) =>
    setExpertVoices((p) => p.map((old, j) => (j === i ? v : old)));

  // ── Voice preview ─────────────────────────────────────────────────────────

  const handlePreview = async (voiceId: string) => {
    const name = voiceName(voiceId);
    const isPlaying = previewingVoice === voiceId;

    // Stop whatever is playing
    if (previewRef.current) {
      previewRef.current.pause();
      previewRef.current.src = '';
      previewRef.current = null;
      setPreviewingVoice(null);
    }
    if (isPlaying) return; // toggle off

    setPreviewingVoice(voiceId);
    try {
      const audio = new Audio(
        `${API}/api/voices/preview?voice=${encodeURIComponent(voiceId)}&name=${encodeURIComponent(name)}`
      );
      previewRef.current = audio;
      const clear = () => { setPreviewingVoice(null); previewRef.current = null; };
      audio.onended = clear;
      audio.onerror = clear;
      await audio.play();
    } catch {
      setPreviewingVoice(null);
    }
  };

  // ── Voice select widget (reused for host and each expert) ─────────────────

  const VoiceSelect = ({
    value, disabled, onChange, onPreview, isPreviewing,
  }: {
    value: string;
    disabled: Set<string>;
    onChange: (v: string) => void;
    onPreview: () => void;
    isPreviewing: boolean;
  }) => (
    <div className="flex items-center gap-2 flex-1">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {Object.entries(voiceOptions).map(([id, label]) => (
          <option key={id} value={id} disabled={disabled.has(id)}>
            {label}
          </option>
        ))}
      </select>
      <button
        onClick={onPreview}
        title={isPreviewing ? 'Stop preview' : `Preview ${voiceName(value)}`}
        className={`flex-shrink-0 w-8 h-8 rounded-lg text-sm flex items-center justify-center transition-colors ${
          isPreviewing
            ? 'bg-blue-600 text-white animate-pulse'
            : 'bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200'
        }`}
      >
        {isPreviewing ? '■' : '▶'}
      </button>
    </div>
  );

  // ── SSE helper ────────────────────────────────────────────────────────────

  function openStream(id: string, fetchScriptOnDone: boolean) {
    esRef.current?.close();
    doneRef.current = false;
    const es = new EventSource(`${API}/api/jobs/${id}/events`);
    esRef.current = es;

    es.onmessage = (e) => {
      const event: SseEvent = JSON.parse(e.data);
      if (event.stage === 'ping') return;
      setEvents((prev) => [...prev, event]);

      if (event.stage === 'done') {
        doneRef.current = true;
        es.close();
        setPhase('done');
        if (fetchScriptOnDone) {
          fetch(`${API}/api/jobs/${id}/script`)
            .then((r) => r.json()).then(setScript).catch(() => {});
        }
      } else if (event.stage === 'error') {
        doneRef.current = true;
        es.close();
        setPhase('error');
        setErrorMsg(event.message);
      }
    };

    es.onerror = () => {
      if (!doneRef.current) {
        es.close();
        setPhase('error');
        setErrorMsg('Lost connection to the server. Is the orchestrator running?');
      }
    };
  }

  // ── Generate ──────────────────────────────────────────────────────────────

  const generate = useCallback(async () => {
    if (!topic.trim()) return;
    setIsRegen(false);
    setPhase('generating');
    setEvents([]);
    setJobId(null);
    setScript(null);
    setErrorMsg('');

    let id: string | null = null;
    try {
      const res = await fetch(`${API}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          duration_minutes: duration,
          voices: { host: hostVoice, experts: expertVoices },
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      id = (await res.json()).job_id as string;
    } catch (e) {
      setPhase('error');
      setErrorMsg(`Could not reach the orchestrator: ${e instanceof Error ? e.message : e}`);
      return;
    }
    if (!id) return;
    setJobId(id);
    openStream(id, true);
  }, [topic, duration, hostVoice, expertVoices]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Regen audio ───────────────────────────────────────────────────────────

  const regenAudio = useCallback(async () => {
    if (!jobId) return;
    setIsRegen(true);
    setPhase('generating');
    setEvents([]);
    setErrorMsg('');

    try {
      const res = await fetch(`${API}/api/jobs/${jobId}/regen-audio`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (e) {
      setPhase('error');
      setErrorMsg(`Regeneration failed: ${e instanceof Error ? e.message : e}`);
      return;
    }
    openStream(jobId, false);
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Reset ─────────────────────────────────────────────────────────────────

  const reset = () => {
    esRef.current?.close();
    setPhase('idle'); setIsRegen(false);
    setEvents([]); setJobId(null); setScript(null); setErrorMsg('');
  };

  // ── Script → Markdown ─────────────────────────────────────────────────────

  const downloadScript = () => {
    if (!script) return;
    const names = script.speaker_names ?? {};
    let md = `# ${script.topic}\n\n*${script.duration_minutes} minute podcast*\n\n---\n\n`;
    let lastSeg = '';
    for (const line of script.lines) {
      if (line.segment !== lastSeg) {
        md += `\n## ${line.segment.toUpperCase()}\n\n`;
        lastSeg = line.segment;
      }
      md += `**${names[line.speaker] ?? line.speaker}:** ${line.text}\n\n`;
    }
    Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(new Blob([md], { type: 'text/markdown' })),
      download: `${slugify(script.topic)}.md`,
    }).click();
  };

  // ── Derived ───────────────────────────────────────────────────────────────

  const stageOrder   = isRegen ? REGEN_STAGES : ALL_STAGES;
  const currentStage = events.length > 0 ? events[events.length - 1].stage : '';
  const currentIdx   = stageOrder.indexOf(currentStage as StageId);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6 md:p-10">
      <div className="max-w-2xl mx-auto space-y-8">

        {/* Header */}
        <div className="text-center space-y-2 pt-6">
          <h1 className="text-3xl font-bold tracking-tight">Personal Podcast Generator</h1>
          <p className="text-gray-400 text-sm">Turn any topic into a multi-voice podcast — no API key needed</p>
        </div>

        {/* ── Form ──────────────────────────────────────────────────────────── */}
        {(phase === 'idle' || phase === 'error') && (
          <div className="bg-gray-900 rounded-xl p-6 space-y-5 border border-gray-800">

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Topic</label>
              <textarea
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. How React Server Components work"
                rows={3}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Duration</label>
              <div className="flex gap-2">
                {DURATIONS.map((d) => (
                  <button key={d} onClick={() => setDuration(d)}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                      duration === d ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                    }`}>
                    {d} min
                  </button>
                ))}
              </div>
            </div>

            {/* ── Voice settings ──────────────────────────────────────────── */}
            <div className="border border-gray-800 rounded-lg overflow-hidden">
              <button
                onClick={() => setVoicesOpen((o) => !o)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              >
                <span>Voice settings</span>
                <span className="text-xs">{voicesOpen ? '▲' : '▼'}</span>
              </button>

              {voicesOpen && (
                <div className="border-t border-gray-800 p-4 space-y-4">

                  {/* Host */}
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Host</p>
                    <VoiceSelect
                      value={hostVoice}
                      disabled={usedBy('host')}
                      onChange={setHostVoice}
                      onPreview={() => handlePreview(hostVoice)}
                      isPreviewing={previewingVoice === hostVoice}
                    />
                  </div>

                  {/* Experts */}
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Experts ({expertVoices.length})
                    </p>
                    <div className="space-y-2">
                      {expertVoices.map((voice, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <VoiceSelect
                            value={voice}
                            disabled={usedBy(i)}
                            onChange={(v) => changeExpert(i, v)}
                            onPreview={() => handlePreview(voice)}
                            isPreviewing={previewingVoice === voice}
                          />
                          {expertVoices.length > 1 && (
                            <button
                              onClick={() => removeExpert(i)}
                              title="Remove this expert"
                              className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-800 hover:bg-red-900 text-gray-500 hover:text-red-300 text-sm flex items-center justify-center transition-colors"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    {expertVoices.length < 3 && (
                      <button
                        onClick={addExpert}
                        className="mt-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        + Add expert
                      </button>
                    )}
                  </div>

                </div>
              )}
            </div>

            {phase === 'error' && (
              <div className="bg-red-950 border border-red-800 rounded-lg p-3 text-red-300 text-sm">
                {errorMsg}
              </div>
            )}

            <button
              onClick={generate}
              disabled={!topic.trim()}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              Generate Podcast
            </button>
          </div>
        )}

        {/* ── Progress ──────────────────────────────────────────────────────── */}
        {phase === 'generating' && (
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-5">
            <div>
              <p className="text-xs text-gray-500">{isRegen ? 'Regenerating audio for' : 'Generating'}</p>
              <p className="font-medium text-sm mt-0.5">{topic}</p>
            </div>
            <div className="space-y-3">
              {stageOrder.map((s, i) => {
                const done   = currentIdx > i;
                const active = currentStage === s;
                return (
                  <div key={s} className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                      done ? 'bg-green-600 text-white' : active ? 'bg-blue-600 text-white animate-pulse' : 'bg-gray-800 text-gray-600'
                    }`}>
                      {done ? '✓' : i + 1}
                    </div>
                    <span className={`text-sm transition-colors ${active ? 'text-white font-medium' : done ? 'text-gray-400' : 'text-gray-600'}`}>
                      {STAGE_LABELS[s]}
                    </span>
                    {active && events.length > 0 && (
                      <span className="text-xs text-gray-500 ml-auto truncate max-w-[40%]">
                        {events[events.length - 1].message}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Result ────────────────────────────────────────────────────────── */}
        {phase === 'done' && jobId && (
          <div className="space-y-4">
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-500">Podcast</p>
                  <p className="font-semibold text-sm mt-0.5">{topic}</p>
                </div>
                <span className="text-xs text-green-400 bg-green-950 border border-green-900 px-2 py-1 rounded-full">Ready</span>
              </div>

              <audio key={`${jobId}-${events.length}`} controls src={`${API}/api/jobs/${jobId}/audio`} className="w-full" />

              <div className="flex gap-2 flex-wrap">
                <a
                  href={`${API}/api/jobs/${jobId}/audio`}
                  download={`${slugify(topic)}.mp3`}
                  className="flex-1 text-center bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium py-2 rounded-lg transition-colors"
                >
                  Download MP3
                </a>
                {script && (
                  <button onClick={downloadScript}
                    className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium py-2 rounded-lg transition-colors">
                    Download Script
                  </button>
                )}
                <button onClick={regenAudio}
                  title="Re-synthesize with different voices without re-running research"
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium py-2 rounded-lg transition-colors">
                  Regenerate Audio
                </button>
              </div>
            </div>

            {/* Script viewer */}
            {script && (
              <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                <button
                  onClick={() => setScriptOpen((o) => !o)}
                  className="w-full flex items-center justify-between px-6 py-4 text-sm font-medium text-gray-300 hover:text-white transition-colors"
                >
                  <span>View Script ({script.lines.length} lines)</span>
                  <span className="text-gray-600 text-xs">{scriptOpen ? '▲' : '▼'}</span>
                </button>

                {scriptOpen && (
                  <div className="border-t border-gray-800 divide-y divide-gray-800/50 max-h-[28rem] overflow-y-auto">
                    {script.lines.map((line, i) => {
                      const isHost = line.speaker === 'host';
                      const name   = script.speaker_names?.[line.speaker] ?? line.speaker;
                      return (
                        <div key={i} className={`px-6 py-3 flex gap-3 ${!isHost ? 'flex-row-reverse bg-gray-900/50' : ''}`}>
                          <div className={`flex-shrink-0 w-7 h-7 rounded-full text-xs flex items-center justify-center font-bold ${speakerBadgeClass(line.speaker)}`}>
                            {name[0]?.toUpperCase() ?? '?'}
                          </div>
                          <p className={`text-sm text-gray-300 leading-relaxed max-w-[85%] ${!isHost ? 'text-right' : ''}`}>
                            {line.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            <button onClick={reset}
              className="w-full bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-gray-200 text-sm font-medium py-2.5 rounded-xl transition-colors">
              Generate Another Podcast
            </button>
          </div>
        )}

      </div>
    </main>
  );
}
