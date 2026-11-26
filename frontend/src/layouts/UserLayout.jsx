import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Search,
  BookOpen,
  Menu,
  X,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'

const SIDEBAR_WIDTH_KEY = 'topicdoc-user-sidebar-width'
const LAST_EXPANDED_WIDTH_KEY = 'topicdoc-user-sidebar-last-expanded-width'
const MIN_SIDEBAR_WIDTH = 64
const MAX_SIDEBAR_WIDTH = 420
const DEFAULT_SIDEBAR_WIDTH = 256
const COMPACT_BREAKPOINT = 210
const BRAND_BREAKPOINT = 245

function readWidth(key, fallback, min = MIN_SIDEBAR_WIDTH) {
  try {
    const value = Number(window.localStorage.getItem(key))
    return Number.isFinite(value) && value >= min
      ? Math.min(MAX_SIDEBAR_WIDTH, value)
      : fallback
  } catch {
    return fallback
  }
}

export default function UserLayout() {
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    readWidth(SIDEBAR_WIDTH_KEY, DEFAULT_SIDEBAR_WIDTH),
  )
  const [lastExpandedWidth, setLastExpandedWidth] = useState(() =>
    readWidth(LAST_EXPANDED_WIDTH_KEY, DEFAULT_SIDEBAR_WIDTH, COMPACT_BREAKPOINT),
  )
  const [isResizing, setIsResizing] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const location = useLocation()

  const isCollapsed = sidebarWidth <= 80
  const isCompact = sidebarWidth < COMPACT_BREAKPOINT
  const showBrand = sidebarWidth >= BRAND_BREAKPOINT

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth))
      if (sidebarWidth >= COMPACT_BREAKPOINT) {
        window.localStorage.setItem(LAST_EXPANDED_WIDTH_KEY, String(sidebarWidth))
      }
    } catch {
      // The layout remains usable when browser storage is unavailable.
    }
  }, [sidebarWidth])

  useEffect(() => {
    setIsMobileOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!isMobileOpen) return undefined
    function handleKeyDown(event) {
      if (event.key === 'Escape') setIsMobileOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMobileOpen])

  useEffect(() => {
    if (!isResizing) return undefined
    function stopResize() {
      setIsResizing(false)
    }
    window.addEventListener('pointerup', stopResize)
    window.addEventListener('pointercancel', stopResize)
    return () => {
      window.removeEventListener('pointerup', stopResize)
      window.removeEventListener('pointercancel', stopResize)
    }
  }, [isResizing])

  function toggleSidebar() {
    if (isCollapsed) {
      setSidebarWidth(Math.max(COMPACT_BREAKPOINT, lastExpandedWidth))
    } else {
      setLastExpandedWidth(sidebarWidth)
      setSidebarWidth(MIN_SIDEBAR_WIDTH)
    }
  }

  function handleResizePointerDown(event) {
    if (event.button !== 0) return
    event.preventDefault()
    event.currentTarget.setPointerCapture?.(event.pointerId)
    setIsResizing(true)
  }

  function handleResizePointerMove(event) {
    if (!isResizing) return
    const nextWidth = Math.min(
      MAX_SIDEBAR_WIDTH,
      Math.max(MIN_SIDEBAR_WIDTH, event.clientX),
    )
    setSidebarWidth(nextWidth)
    if (nextWidth >= COMPACT_BREAKPOINT) setLastExpandedWidth(nextWidth)
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-800">
      {isMobileOpen && (
        <button
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setIsMobileOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-[1px] md:hidden"
        />
      )}

      <aside
        id="user-sidebar"
        aria-label="User navigation"
        style={{ '--sidebar-width': `${sidebarWidth}px` }}
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden border-r border-slate-200 bg-white shadow-xl transition-[width,transform] duration-200 ease-out md:relative md:z-auto md:w-[var(--sidebar-width)] md:translate-x-0 md:shadow-none ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${isResizing ? 'md:select-none md:transition-none' : ''}`}
      >
        <div className={`flex h-16 shrink-0 items-center border-b border-slate-200 ${
          isCompact ? 'justify-center px-2' : 'gap-3 px-5'
        }`}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <BookOpen size={20} />
          </div>
          {showBrand && (
            <span className="min-w-0 whitespace-nowrap text-lg font-bold tracking-tight">
              TopicDoc <span className="text-indigo-600">Finder</span>
            </span>
          )}
          <button
            type="button"
            onClick={() => setIsMobileOpen(false)}
            aria-label="Close navigation menu"
            className="ml-auto rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 md:hidden"
          >
            <X size={19} />
          </button>
        </div>

        <nav className={`flex-1 overflow-x-hidden overflow-y-auto py-6 ${isCompact ? 'px-2' : 'px-3'}`}>
          {!isCompact && (
            <p className="mb-3 whitespace-nowrap px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Workspace
            </p>
          )}
          <NavLink
            to="/"
            end
            title={isCompact ? 'Knowledge Base Search' : undefined}
            aria-label="Knowledge Base Search"
            onClick={() => setIsMobileOpen(false)}
            className={({ isActive }) =>
              `flex min-h-11 items-center rounded-lg text-sm font-medium transition-colors ${
                isCompact ? 'justify-center px-0' : 'gap-3 px-3'
              } ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            <Search size={19} className="shrink-0" />
            {!isCompact && <span className="min-w-0 truncate">Knowledge Base Search</span>}
          </NavLink>
        </nav>

        <div className={`mt-auto shrink-0 border-t border-slate-200 py-3 ${isCompact ? 'px-2' : 'px-3'}`}>
          <div
            className={`rounded-xl border border-slate-200 bg-slate-50 p-3 ${
              isCompact ? 'flex justify-center border-0 bg-transparent p-0' : ''
            }`}
            title={isCompact ? 'Knowledge Base' : undefined}
          >
            <BookOpen size={19} className={`shrink-0 text-indigo-600 ${isCompact ? 'block' : 'hidden'}`} />
            {!isCompact && (
              <div>
                <p className="text-sm font-medium text-slate-700">Knowledge Base</p>
                <p className="mt-1 text-xs text-slate-500">Search indexed research documents.</p>
              </div>
            )}
          </div>
        </div>

        <div
          role="separator"
          aria-label="Resize sidebar"
          aria-orientation="vertical"
          aria-valuemin={MIN_SIDEBAR_WIDTH}
          aria-valuemax={MAX_SIDEBAR_WIDTH}
          aria-valuenow={Math.round(sidebarWidth)}
          tabIndex={0}
          onPointerDown={handleResizePointerDown}
          onPointerMove={handleResizePointerMove}
          onPointerUp={() => setIsResizing(false)}
          onPointerCancel={() => setIsResizing(false)}
          onDoubleClick={() => setSidebarWidth(DEFAULT_SIDEBAR_WIDTH)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowLeft') setSidebarWidth((w) => Math.max(MIN_SIDEBAR_WIDTH, w - 12))
            if (event.key === 'ArrowRight') setSidebarWidth((w) => Math.min(MAX_SIDEBAR_WIDTH, w + 12))
          }}
          className="group absolute right-[-5px] top-0 z-30 hidden h-full w-[10px] cursor-col-resize touch-none md:block"
          title="Drag to resize or collapse · Double-click to reset"
        >
          <span className="absolute inset-y-0 left-[4px] w-[2px] bg-transparent transition-colors group-hover:bg-indigo-400 group-focus-visible:bg-indigo-500" />
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setIsMobileOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={isMobileOpen}
              aria-controls="user-sidebar"
              className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 md:hidden"
            >
              <Menu size={21} />
            </button>
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-expanded={!isCollapsed}
              aria-controls="user-sidebar"
              className="hidden rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 md:inline-flex"
            >
              {isCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
            </button>
            <p className="truncate text-sm font-medium text-slate-600">Research Knowledge Base</p>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-sm text-slate-500">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            <span className="hidden sm:inline">Knowledge Base</span>
          </div>
        </header>

        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
