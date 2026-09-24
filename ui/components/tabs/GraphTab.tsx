'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ZoomIn, ZoomOut, Maximize, RotateCcw, X } from 'lucide-react';
import { SubgraphResponse, GraphNode } from '@/lib/types';

interface GraphTabProps {
  caseId: string;
}

export function GraphTab({ caseId }: GraphTabProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [subgraph, setSubgraph] = useState<SubgraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Fetch subgraph data
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetch(`/api/cases/${caseId}/subgraph`)
      .then((res) => res.json())
      .then((data: SubgraphResponse) => {
        if (isMounted) {
          setSubgraph(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load subgraph:', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [caseId]);

  // Initialize Cytoscape
  useEffect(() => {
    if (!subgraph || !containerRef.current) return;

    let cyInstance: any = null;

    import('cytoscape').then(async (cytoscapeModule) => {
      const cytoscape = cytoscapeModule.default;

      // Try registering fcose layout if available
      try {
        const fcose = (await import('cytoscape-fcose')).default;
        cytoscape.use(fcose);
      } catch {
        // Fallback to standard cose
      }

      // Convert nodes to Cytoscape elements
      const elements: any[] = [];

      subgraph.nodes.forEach((n) => {
        let shape = 'ellipse';
        let size = 20;
        let color = '#9AA8B5';

        if (n.type === 'Customer') {
          color = '#58A6FF';
          size = 28;
        } else if (n.type === 'Card') {
          color = '#F5A524';
          size = 22;
        } else if (n.type === 'Transaction') {
          color = n.properties?.flagged ? '#E5484D' : '#5C6B7A';
          size = n.properties?.flagged ? 12 : 8;
        } else if (n.type === 'DeviceProfile') {
          color = n.properties?.shared_device ? '#E5484D' : '#9AA8B5';
          size = 20;
        } else if (n.type === 'ClosedCase') {
          color = '#2DD4BF';
          shape = 'diamond';
          size = 22;
        } else if (n.type === 'BillingRegion') {
          color = '#9AA8B6';
          shape = 'rectangle';
          size = 20;
        } else if (n.type === 'InvestigationCase') {
          color = '#F5A524';
          size = 26;
        }

        elements.push({
          data: {
            id: n.id,
            label: n.label,
            type: n.type,
            properties: n.properties,
            color,
            size,
            shape,
            isShared: Boolean(n.properties?.shared_device),
          },
        });
      });

      subgraph.edges.forEach((e, idx) => {
        let lineStyle = 'solid';
        let lineColor = '#1E2933';

        if (e.relationship === 'FROM_DEVICE') {
          lineColor = '#E5484D';
          lineStyle = 'solid';
        } else if (e.relationship === 'NEXT') {
          lineStyle = 'dashed';
          lineColor = '#5C6B7A';
        } else if (e.relationship === 'PRIOR_CASE_ON' || e.relationship === 'RECALLS_MEMORY') {
          lineColor = '#2DD4BF';
          lineStyle = 'dotted';
        } else if (e.relationship === 'SHARED_WITH') {
          lineColor = '#E5484D';
          lineStyle = 'dashed';
        }

        elements.push({
          data: {
            id: `edge-${idx}`,
            source: e.source,
            target: e.target,
            label: e.label || e.relationship,
            lineStyle,
            lineColor,
          },
        });
      });

      if (cyRef.current) {
        cyRef.current.destroy();
      }

      cyInstance = cytoscape({
        container: containerRef.current,
        elements,
        boxSelectionEnabled: false,
        autounselectify: false,
        style: ([
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              'width': 'data(size)',
              'height': 'data(size)',
              'shape': 'data(shape)',
              'label': 'data(label)',
              'font-family': 'var(--font-mono), monospace',
              'font-size': '10px',
              'color': '#9AA8B5',
              'text-valign': 'bottom',
              'text-margin-y': 6,
              'border-width': 1.5,
              'border-color': '#10161D',
            },
          },
          {
            selector: 'node[?isShared]',
            style: {
              'border-width': 2.5,
              'border-color': '#E5484D',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.5,
              'line-color': 'data(lineColor)',
              'line-style': 'data(lineStyle)',
              'target-arrow-color': 'data(lineColor)',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.8,
              'opacity': 0.75,
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': '#F5A524',
              'border-opacity': 1,
            },
          },
          {
            selector: '.dimmed',
            style: {
              'opacity': 0.25,
            },
          },
          {
            selector: '.highlighted',
            style: {
              'opacity': 1,
              'z-index': 999,
            },
          },
        ] as any),
        layout: {
          name: 'cose',
          animate: true,
          randomize: false,
          componentSpacing: 60,
          nodeOverlap: 20,
          idealEdgeLength: 60,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
        },
      });

      // Node Click: Highlight 1-hop neighborhood & dim rest
      cyInstance.on('tap', 'node', (evt: any) => {
        const node = evt.target;
        const neighborhood = node.neighborhood().add(node);

        cyInstance.elements().removeClass('highlighted').addClass('dimmed');
        neighborhood.removeClass('dimmed').addClass('highlighted');

        const originalNode = subgraph.nodes.find((n) => n.id === node.id());
        setSelectedNode(originalNode || null);
      });

      // Tap Background: Clear Focus
      cyInstance.on('tap', (evt: any) => {
        if (evt.target === cyInstance) {
          cyInstance.elements().removeClass('dimmed highlighted');
          setSelectedNode(null);
        }
      });

      cyRef.current = cyInstance;
    });

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [subgraph]);

  function handleZoomIn() {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  }

  function handleZoomOut() {
    cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  }

  function handleFit() {
    cyRef.current?.fit(undefined, 40);
  }

  function handleResetFocus() {
    if (cyRef.current) {
      cyRef.current.elements().removeClass('dimmed highlighted');
      cyRef.current.fit(undefined, 40);
    }
    setSelectedNode(null);
  }

  return (
    <div className="relative w-full h-[calc(100vh-230px)] min-h-[500px] select-none bg-[#0A0E13]">
      {/* Cytoscape Canvas with Dot Grid */}
      <div
        ref={containerRef}
        className="w-full h-full cytoscape-grid"
      />

      {/* Loading Shimmer */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0A0E13]/80 backdrop-blur-sm z-20">
          <div className="flex items-center gap-2 font-mono text-xs text-[#9AA8B5] bg-[#10161D] border border-[#1E2933] px-3 py-1.5 rounded-[6px]">
            <span className="w-2 h-2 rounded-full bg-[#F5A524] animate-ping" />
            <span>Traversing TigerGraph Topology...</span>
          </div>
        </div>
      )}

      {/* Top-Left Legend Overlay */}
      <div className="absolute top-4 left-4 z-10 bg-[#10161D] border border-[#1E2933] rounded-[6px] p-2.5 flex flex-col gap-1.5 shadow-sm">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#5C6B7A] mb-0.5">
          Entity Legend
        </span>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-3.5 h-3.5 rounded-full bg-[#58A6FF]" />
          <span>Customer (28px)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-3 h-3 rounded-full bg-[#F5A524]" />
          <span>Card (22px)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-2 h-2 rounded-full bg-[#5C6B7A]" />
          <span>Transaction (8px)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-3 h-3 rounded-full bg-[#E5484D]" />
          <span>Shared Device (R6)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-3 h-3 rotate-45 bg-[#2DD4BF]" />
          <span>Closed Case (Diamond)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#9AA8B5]">
          <span className="w-3 h-3 bg-[#9AA8B6]" />
          <span>Billing Region (Square)</span>
        </div>
      </div>

      {/* Bottom-Right Controls Group */}
      <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-1 bg-[#161E27] border border-[#1E2933] rounded-[6px] p-1 shadow-sm">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="w-8 h-8 flex items-center justify-center text-[#9AA8B5] hover:text-[#E8EEF4] hover:bg-[#10161D] rounded transition-colors"
        >
          <ZoomIn className="w-4 h-4" strokeWidth={1.5} />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="w-8 h-8 flex items-center justify-center text-[#9AA8B5] hover:text-[#E8EEF4] hover:bg-[#10161D] rounded transition-colors"
        >
          <ZoomOut className="w-4 h-4" strokeWidth={1.5} />
        </button>
        <button
          onClick={handleFit}
          title="Fit View"
          className="w-8 h-8 flex items-center justify-center text-[#9AA8B5] hover:text-[#E8EEF4] hover:bg-[#10161D] rounded transition-colors"
        >
          <Maximize className="w-4 h-4" strokeWidth={1.5} />
        </button>
        <button
          onClick={handleResetFocus}
          title="Clear Focus"
          className="w-8 h-8 flex items-center justify-center text-[#9AA8B5] hover:text-[#E8EEF4] hover:bg-[#10161D] rounded transition-colors"
        >
          <RotateCcw className="w-4 h-4" strokeWidth={1.5} />
        </button>
      </div>

      {/* Node Inspector Side Panel (when node clicked) */}
      {selectedNode && (
        <div className="absolute top-4 right-4 z-20 w-80 bg-[#10161D] border border-[#1E2933] rounded-[8px] p-3.5 shadow-lg flex flex-col gap-2.5">
          <div className="flex items-center justify-between border-b border-[#1E2933] pb-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-[#E8EEF4]">
                {selectedNode.type}
              </span>
              <span className="font-mono text-[11px] text-[#9AA8B5]">
                {selectedNode.id}
              </span>
            </div>
            <button
              onClick={() => handleResetFocus()}
              className="text-[#5C6B7A] hover:text-[#E8EEF4] transition-colors"
            >
              <X className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </div>

          <div className="flex flex-col gap-1.5 font-mono text-[11px]">
            {Object.entries(selectedNode.properties || {}).map(([k, v]) => {
              if (v === undefined || v === null) return null;
              return (
                <div key={k} className="flex justify-between gap-2 py-0.5 border-b border-[#1E2933]/50">
                  <span className="text-[#5C6B7A]">{k}:</span>
                  <span className="text-[#E8EEF4] text-right truncate max-w-[180px]">
                    {typeof v === 'number' ? v.toFixed(2) : String(v)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
