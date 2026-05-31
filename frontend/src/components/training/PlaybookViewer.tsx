import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Search, BookOpen, Plug, Camera as CameraIcon, Sparkles, Wrench, ClipboardList, FileText } from 'lucide-react'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import playbookData from '@/data/playbook.json'

const PLAYBOOK = playbookData as Record<string, string>

interface PlaybookViewerProps {
  country: 'canada' | 'us'
}

interface TreeNode {
  key: string
  label: string
  children: TreeNode[]
  filePath?: string
}

const SECTION_META: Record<string, { label: string; icon: typeof BookOpen; order: number }> = {
  '00-getting-started':     { label: 'Getting Started',      icon: BookOpen,      order: 0 },
  '10-pos-integrations':    { label: 'POS Integrations',     icon: Plug,          order: 1 },
  '20-camera-integrations': { label: 'Camera Integrations',  icon: CameraIcon,    order: 2 },
  '30-features':            { label: 'Features',             icon: Sparkles,      order: 3 },
  '40-troubleshooting':     { label: 'Troubleshooting',      icon: Wrench,        order: 4 },
  '50-cheatsheets':         { label: 'Cheat Sheets',         icon: ClipboardList, order: 5 },
}

const HIDDEN_PREFIXES = ['_template']

function titleFromPath(path: string): string {
  const filename = path.split('/').pop() ?? path
  const stem = filename.replace(/\.md$/, '')
  if (stem === 'README') return 'Overview'
  if (stem === '_index') return 'Index'
  if (stem === '_open-questions') return 'Open Questions'
  return stem
    .replace(/^\d+-/, '')
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

function buildTree(paths: string[]): TreeNode[] {
  const sections = new Map<string, TreeNode>()

  for (const path of paths) {
    const parts = path.split('/')
    const sectionKey = parts[0]
    const filename = parts[parts.length - 1].replace(/\.md$/, '')
    if (HIDDEN_PREFIXES.some(p => filename.startsWith(p))) continue

    if (!SECTION_META[sectionKey]) {
      if (parts.length === 1 && (filename === 'README' || filename === '_open-questions')) continue
      continue
    }

    if (!sections.has(sectionKey)) {
      sections.set(sectionKey, {
        key: sectionKey,
        label: SECTION_META[sectionKey].label,
        children: [],
      })
    }
    const section = sections.get(sectionKey)!

    let parent = section
    for (let i = 1; i < parts.length - 1; i++) {
      const subKey = parts.slice(0, i + 1).join('/')
      let sub = parent.children.find(c => c.key === subKey)
      if (!sub) {
        sub = { key: subKey, label: titleFromPath(parts[i] + '/'), children: [] }
        parent.children.push(sub)
      }
      parent = sub
    }

    parent.children.push({
      key: path,
      label: titleFromPath(path),
      children: [],
      filePath: path,
    })
  }

  for (const section of sections.values()) {
    sortTree(section.children)
  }

  return Array.from(sections.values()).sort(
    (a, b) => (SECTION_META[a.key]?.order ?? 99) - (SECTION_META[b.key]?.order ?? 99),
  )
}

function sortTree(nodes: TreeNode[]) {
  nodes.sort((a, b) => {
    // index files first within a section
    const aIsIndex = a.label === 'Index'
    const bIsIndex = b.label === 'Index'
    if (aIsIndex && !bIsIndex) return -1
    if (!aIsIndex && bIsIndex) return 1
    return a.label.localeCompare(b.label)
  })
  for (const node of nodes) sortTree(node.children)
}

export function PlaybookViewer({ country: _country }: PlaybookViewerProps) {
  const tree = useMemo(() => buildTree(Object.keys(PLAYBOOK)), [])
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['00-getting-started']))
  const [selectedPath, setSelectedPath] = useState<string>('00-getting-started/01-welcome.md')
  const [query, setQuery] = useState('')

  const filteredTree = useMemo(() => {
    if (!query.trim()) return tree
    const q = query.toLowerCase()
    return tree
      .map(section => filterNode(section, q))
      .filter((s): s is TreeNode => s !== null)
  }, [tree, query])

  const content = PLAYBOOK[selectedPath] ?? '# Not found\n\nSelect a topic from the left.'

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 min-h-[600px]">
      {/* Tree nav */}
      <aside className="lg:w-72 flex-shrink-0">
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl overflow-hidden">
          <div className="p-3 border-b border-[#1a2420]">
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#4a5550]" />
              <input
                type="search"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search the playbook…"
                className="w-full pl-7 pr-2 py-1.5 bg-[#1a2420]/60 border border-[#1a2420] rounded-lg text-[11px] text-white placeholder:text-[#4a5550] focus:outline-none focus:border-[#00d4aa]/40"
              />
            </div>
          </div>

          <nav className="max-h-[calc(100vh-220px)] overflow-y-auto p-2">
            {filteredTree.length === 0 && (
              <p className="px-2 py-3 text-[11px] text-[#6b7a74]">No matches.</p>
            )}
            {filteredTree.map(section => (
              <TreeSection
                key={section.key}
                node={section}
                level={0}
                expanded={expanded}
                setExpanded={setExpanded}
                selectedPath={selectedPath}
                onSelect={setSelectedPath}
              />
            ))}
          </nav>
        </div>
      </aside>

      {/* Content */}
      <article className="flex-1 min-w-0">
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 lg:p-8 markdown-body">
          <div className="mb-3 text-[10px] uppercase tracking-wider text-[#4a5550] flex items-center gap-1.5">
            <FileText size={11} /> {selectedPath}
          </div>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="text-2xl font-bold text-white mb-4 mt-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-semibold text-white mt-6 mb-2 pb-1 border-b border-[#1a2420]">{children}</h2>,
              h3: ({ children }) => <h3 className="text-[14px] font-semibold text-white mt-4 mb-2">{children}</h3>,
              p: ({ children }) => <p className="text-[13px] leading-relaxed text-[#c8d0cc] mb-3">{children}</p>,
              ul: ({ children }) => <ul className="text-[13px] text-[#c8d0cc] mb-3 ml-5 list-disc space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="text-[13px] text-[#c8d0cc] mb-3 ml-5 list-decimal space-y-1">{children}</ol>,
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#00d4aa] hover:underline">
                  {children}
                </a>
              ),
              code: ({ children, className }) => {
                const isInline = !className
                return isInline
                  ? <code className="px-1 py-0.5 bg-[#1a2420] rounded text-[#00d4aa] text-[12px] font-mono">{children}</code>
                  : <code className="block p-3 bg-[#1a2420]/60 rounded-lg text-[12px] font-mono text-[#c8d0cc] overflow-x-auto">{children}</code>
              },
              pre: ({ children }) => <pre className="mb-3">{children}</pre>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-[#00d4aa]/40 pl-4 py-1 my-3 text-[#9ca3a0] text-[13px] italic">
                  {children}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto mb-3">
                  <table className="min-w-full text-[12px] border-collapse">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="border-b border-[#1a2420]">{children}</thead>,
              th: ({ children }) => <th className="px-3 py-2 text-left font-semibold text-white">{children}</th>,
              td: ({ children }) => <td className="px-3 py-2 text-[#c8d0cc] border-b border-[#1a2420]/40 align-top">{children}</td>,
              hr: () => <hr className="my-5 border-[#1a2420]" />,
              strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </article>
    </div>
  )
}

interface TreeSectionProps {
  node: TreeNode
  level: number
  expanded: Set<string>
  setExpanded: (s: Set<string>) => void
  selectedPath: string
  onSelect: (path: string) => void
}

function TreeSection({ node, level, expanded, setExpanded, selectedPath, onSelect }: TreeSectionProps) {
  const isOpen = expanded.has(node.key)
  const isLeaf = node.children.length === 0 && node.filePath
  const isSelected = isLeaf && node.filePath === selectedPath

  const Icon = level === 0 ? SECTION_META[node.key]?.icon ?? FileText : null

  const toggle = () => {
    const next = new Set(expanded)
    if (next.has(node.key)) next.delete(node.key)
    else next.add(node.key)
    setExpanded(next)
  }

  if (isLeaf) {
    return (
      <button
        onClick={() => onSelect(node.filePath!)}
        className={clsx(
          'w-full text-left px-2.5 py-1.5 rounded-md text-[12px] transition-colors',
          'flex items-center gap-1.5',
          isSelected ? 'bg-[#00d4aa]/10 text-[#00d4aa]' : 'text-[#9ca3a0] hover:bg-[#1a2420]/40 hover:text-white',
        )}
        style={{ paddingLeft: `${10 + level * 14}px` }}
      >
        <FileText size={10} className="opacity-50 flex-shrink-0" />
        <span className="truncate">{node.label}</span>
      </button>
    )
  }

  return (
    <div className="mb-0.5">
      <button
        onClick={toggle}
        className={clsx(
          'w-full text-left px-2.5 py-1.5 rounded-md text-[11px] font-semibold transition-colors',
          'flex items-center gap-1.5',
          level === 0 ? 'text-white uppercase tracking-wider' : 'text-[#c8d0cc]',
          'hover:bg-[#1a2420]/40',
        )}
        style={{ paddingLeft: `${6 + level * 14}px` }}
      >
        {isOpen ? <ChevronDown size={11} className="text-[#4a5550] flex-shrink-0" /> : <ChevronRight size={11} className="text-[#4a5550] flex-shrink-0" />}
        {Icon && <Icon size={12} className="text-[#00d4aa] flex-shrink-0" />}
        <span className="truncate">{node.label}</span>
      </button>
      {isOpen && (
        <div className="mt-0.5">
          {node.children.map(child => (
            <TreeSection
              key={child.key}
              node={child}
              level={level + 1}
              expanded={expanded}
              setExpanded={setExpanded}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function filterNode(node: TreeNode, q: string): TreeNode | null {
  // match on label OR on file content
  const labelHit = node.label.toLowerCase().includes(q)
  const contentHit = node.filePath ? (PLAYBOOK[node.filePath] ?? '').toLowerCase().includes(q) : false

  if (node.children.length === 0) {
    return (labelHit || contentHit) ? node : null
  }

  const filteredChildren = node.children
    .map(c => filterNode(c, q))
    .filter((c): c is TreeNode => c !== null)

  if (filteredChildren.length === 0 && !labelHit) return null
  return { ...node, children: filteredChildren }
}

export default PlaybookViewer
