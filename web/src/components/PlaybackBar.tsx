import { useEffect } from 'react';

interface PlaybackBarProps {
  currentStep: number;
  totalSteps: number;
  isPlaying: boolean;
  onStepChange: (step: number) => void;
  onTogglePlay: () => void;
}

export function PlaybackBar({
  currentStep,
  totalSteps,
  isPlaying,
  onStepChange,
  onTogglePlay,
}: PlaybackBarProps) {
  const maxIndex = Math.max(0, totalSteps - 1);

  useEffect(() => {
    if (!isPlaying) return;
    if (currentStep >= maxIndex) {
      onTogglePlay();
      return;
    }
    const timer = window.setTimeout(() => {
      onStepChange(currentStep + 1);
    }, 650);
    return () => window.clearTimeout(timer);
  }, [isPlaying, currentStep, maxIndex, onStepChange, onTogglePlay]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        onStepChange(Math.min(maxIndex, currentStep + 1));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        onStepChange(Math.max(0, currentStep - 1));
      } else if (e.key === ' ') {
        e.preventDefault();
        onTogglePlay();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [currentStep, maxIndex, onStepChange, onTogglePlay]);

  return (
    <div className="playback-row">
      <div className="playback-controls">
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => onStepChange(0)}
          disabled={currentStep === 0}
        >
          Início
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => onStepChange(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
        >
          ← Anterior
        </button>
        <button
          type="button"
          className="btn btn-sm btn-primary"
          onClick={() => {
            if (!isPlaying && currentStep >= maxIndex) onStepChange(0);
            onTogglePlay();
          }}
          disabled={maxIndex === 0}
        >
          {isPlaying ? 'Pausar' : 'Reproduzir'}
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => onStepChange(Math.min(maxIndex, currentStep + 1))}
          disabled={currentStep >= maxIndex}
        >
          Próximo →
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => onStepChange(maxIndex)}
          disabled={currentStep >= maxIndex}
        >
          Fim
        </button>
      </div>

      <div className="playback-scrubber">
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={currentStep}
          onChange={(e) => onStepChange(Number(e.target.value))}
          aria-label="Linha do tempo"
        />
        <span className="step-badge">
          Passo {currentStep} / {maxIndex}
        </span>
      </div>
    </div>
  );
}
