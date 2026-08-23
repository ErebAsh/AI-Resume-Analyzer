import React, { useEffect } from 'react'
import { Sparkles, X, Check } from 'lucide-react'
import { CURRENT_RELEASE, markWhatsNewAsSeen, type ReleaseInfo } from '../data/whatsNewReleases'
import './WhatsNewModal.css'

interface WhatsNewModalProps {
  isOpen: boolean
  onClose: () => void
  release?: ReleaseInfo
}

export const WhatsNewModal: React.FC<WhatsNewModalProps> = ({
  isOpen,
  onClose,
  release = CURRENT_RELEASE,
}) => {
  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleDismiss()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, release.version])

  if (!isOpen) return null

  const handleDismiss = () => {
    markWhatsNewAsSeen(release.version)
    onClose()
  }

  const getTagClass = (tag: string) => {
    switch (tag) {
      case 'New':
        return 'whats-new-tag--new'
      case 'Improved':
        return 'whats-new-tag--improved'
      case 'Security':
        return 'whats-new-tag--security'
      default:
        return 'whats-new-tag--fix'
    }
  }

  return (
    <div className="whats-new-overlay" onClick={handleDismiss} data-testid="whats-new-overlay">
      <div
        className="whats-new-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="whats-new-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="whats-new-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
                flexShrink: 0,
              }}
            >
              <Sparkles size={20} />
            </div>
            <div>
              <h2 id="whats-new-title" className="whats-new-title">
                What's New <span className="whats-new-version-badge">v{release.version}</span>
              </h2>
              <p className="whats-new-subtitle">
                Latest releases and architectural updates ({release.date})
              </p>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            aria-label="Close What's New modal"
            className="whats-new-close-btn"
          >
            <X size={20} />
          </button>
        </div>

        {/* Highlight Items List */}
        <div className="whats-new-list">
          {release.highlights.map((item, idx) => {
            const tagClass = getTagClass(item.tag)
            return (
              <div key={idx} className="whats-new-item">
                <span className="whats-new-item-icon">{item.icon || '✨'}</span>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '4px',
                      flexWrap: 'wrap',
                    }}
                  >
                    <span className="whats-new-item-title">{item.title}</span>
                    <span className={`whats-new-tag ${tagClass}`}>{item.tag}</span>
                  </div>
                  <p className="whats-new-item-desc">{item.description}</p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Footer actions */}
        <div className="whats-new-footer">
          <button
            type="button"
            className="app-btn app-btn--primary"
            onClick={handleDismiss}
            style={{
              padding: '8px 22px',
              fontSize: '0.9rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Check size={16} /> Got It, Let's Go!
          </button>
        </div>
      </div>
    </div>
  )
}
