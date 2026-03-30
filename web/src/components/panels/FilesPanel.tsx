import { useState, useEffect, useCallback } from 'react';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  ChevronRight,
  ChevronDown,
  RefreshCw,
} from 'lucide-react';
import type { AgentAdapter, FileNode } from '../../types';

const CODE_EXTENSIONS = new Set([
  '.py',
  '.ts',
  '.tsx',
  '.js',
  '.jsx',
  '.go',
  '.rs',
  '.sh',
  '.toml',
  '.json',
  '.yaml',
  '.yml',
]);

function getFileIcon(name: string) {
  const ext = name.slice(name.lastIndexOf('.'));
  return CODE_EXTENSIONS.has(ext) ? (
    <FileCode
      size={13}
      strokeWidth={1.6}
      style={{ color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
    />
  ) : (
    <FileText
      size={13}
      strokeWidth={1.6}
      style={{ color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
    />
  );
}

function getFileExt(name: string): string | null {
  const idx = name.lastIndexOf('.');
  return idx > 0 ? name.slice(idx + 1) : null;
}

function FileTree({ nodes, depth = 0 }: { nodes: FileNode[]; depth?: number }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <>
      {nodes.map((node) => (
        <div key={node.path}>
          <div
            className="file-tree-row"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              paddingLeft: `${depth * 14 + 8}px`,
              paddingRight: '12px',
              paddingTop: '4px',
              paddingBottom: '4px',
              fontFamily: 'var(--font-body)',
              fontSize: '12px',
              color: 'var(--color-ink-secondary)',
              cursor: 'pointer',
            }}
            onClick={() => {
              if (node.is_dir) setExpanded((e) => ({ ...e, [node.path]: !e[node.path] }));
            }}
          >
            {node.is_dir ? (
              <>
                {expanded[node.path] ? (
                  <ChevronDown
                    size={11}
                    strokeWidth={2}
                    style={{ color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
                  />
                ) : (
                  <ChevronRight
                    size={11}
                    strokeWidth={2}
                    style={{ color: 'var(--color-ink-tertiary)', flexShrink: 0 }}
                  />
                )}
                {expanded[node.path] ? (
                  <FolderOpen
                    size={13}
                    strokeWidth={1.6}
                    style={{ color: 'var(--color-ink-secondary)', flexShrink: 0 }}
                  />
                ) : (
                  <Folder
                    size={13}
                    strokeWidth={1.6}
                    style={{ color: 'var(--color-ink-secondary)', flexShrink: 0 }}
                  />
                )}
              </>
            ) : (
              <>
                <span style={{ width: '11px', flexShrink: 0 }} />
                {getFileIcon(node.name)}
              </>
            )}
            <span
              style={{
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {node.name}
            </span>
            {!node.is_dir && getFileExt(node.name) && (
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '9px',
                  color: 'var(--color-ink-tertiary)',
                  background: 'var(--color-bg-sunken)',
                  padding: '1px 4px',
                  borderRadius: 'var(--radius-sm)',
                  flexShrink: 0,
                }}
              >
                {getFileExt(node.name)}
              </span>
            )}
          </div>
          {node.is_dir && expanded[node.path] && node.children && (
            <FileTree nodes={node.children} depth={depth + 1} />
          )}
        </div>
      ))}
    </>
  );
}

export default function FilesPanel({ adapter }: { adapter: AgentAdapter }) {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchFiles = useCallback(async () => {
    setRefreshing(true);
    try {
      const result = await adapter.listFiles();
      setFiles(result);
    } finally {
      setRefreshing(false);
    }
  }, [adapter]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  return (
    <div style={{ paddingTop: '8px', paddingBottom: '10px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px 6px',
        }}
      >
        <span
          style={{
            flex: 1,
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            fontWeight: 400,
            color: 'var(--color-ink-tertiary)',
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
          }}
        >
          工作区
        </span>
        <button
          aria-label="刷新文件列表"
          onClick={fetchFiles}
          disabled={refreshing}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--color-ink-tertiary)',
            cursor: refreshing ? 'default' : 'pointer',
            padding: '2px',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <RefreshCw
            size={11}
            strokeWidth={1.8}
            style={{
              animation: refreshing ? 'files-spin 0.6s linear infinite' : 'none',
            }}
          />
        </button>
      </div>
      {files.length === 0 ? (
        <div
          style={{
            padding: '0 12px',
            fontSize: 'var(--text-xs)',
            color: 'var(--color-ink-tertiary)',
            fontWeight: 300,
          }}
        >
          无文件
        </div>
      ) : (
        <FileTree nodes={files} />
      )}
    </div>
  );
}
