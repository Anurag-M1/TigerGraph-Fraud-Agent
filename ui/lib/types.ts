/**
 * TigerGraph × HHGOA IEEE Fraud Investigation
 * Data Types & Schema Definitions
 */

export interface EvidenceItem {
  claim: string;
  source: 'graph' | 'customer' | 'analyst' | 'doc' | string;
  ref: string;
  entity_ids?: string[];
}

export interface SimilarPriorCase {
  case_id: string;
  outcome: 'closed_fraud' | 'cleared';
  pattern: string;
  exposure_usd: number;
  similarity_reason?: string;
  closed_at?: string;
}

export interface ActionItem {
  action: string;
  route: 'auto' | 'L1' | 'L2';
  reason: string;
}

export interface NextBestActions {
  initial: ActionItem[];
  final: ActionItem[];
  what_changed: string;
}

export interface SarRecord {
  file: boolean;
  reason: string;
  narrative?: string;
  subjects?: string[];
  total_amount_usd?: number;
  activity_dates?: string[];
}

export interface CasePayload {
  status: 'closed_fraud' | 'closed_legitimate' | 'open';
  verdict: 'fraud' | 'legitimate' | 'uncertain';
  fraud_probability: number;
  pattern: string;
  pattern_description: string;
  affected_txn_ids: string[];
  first_suspicious_txn_id: string;
  connected_card_ids: string[];
  connected_device_profiles: string[];
  exposure_usd: number;
  evidence: EvidenceItem[];
  similar_prior_cases: SimilarPriorCase[] | string[];
  summary: string;
  written_to_graph: boolean;
  graph_case_id: string;
}

export interface EvidenceRequest {
  type: string;
  asked_after_step: number;
  assumed_response: string;
}

export interface CaseFileAnswer {
  case_id: string;
  case: CasePayload;
  evidence_requests?: EvidenceRequest[];
  next_best_actions: NextBestActions;
  sar: SarRecord;
  stop_reason?: string;
  tool_calls?: number;
  tokens?: number;
  latency_s?: number;
}

export interface CaseMetadata {
  case_id: string;
  opened_at: string;
  trigger_type: 'risk_score' | 'customer_report' | 'analyst_request' | string;
  trigger_text: string;
  flagged_txn_id: string;
  card_id: string;
  customer_id: string;
  risk_score?: number | null;
}

export interface CaseSummaryItem {
  case_id: string;
  opened_at: string;
  trigger_type: string;
  trigger_text: string;
  card_id: string;
  customer_id: string;
  risk_score: number | null;
  verdict: 'fraud' | 'legitimate' | 'uncertain';
  status: string;
  fraud_probability: number;
  pattern: string;
  exposure_usd: number;
  sar_file: boolean;
  tool_calls: number;
}

export interface TimelineStepItem {
  step: number;
  node: string;
  title: string;
  description: string;
  duration_ms: number;
  status: string;
  highlight?: boolean;
  asked_after_step?: number;
  raw_payload?: Record<string, unknown>;
}

export interface GraphNode {
  id: string;
  type: 'Customer' | 'Card' | 'Transaction' | 'DeviceProfile' | 'BillingRegion' | 'EmailDomain' | 'ClosedCase' | 'InvestigationCase' | string;
  label: string;
  properties: {
    flagged?: boolean;
    shared_device?: boolean;
    amount?: number;
    channel?: string;
    risk_score?: number;
    timestamp?: number | string;
    connected_card?: boolean;
    full_profile?: string;
    outcome?: string;
    pattern?: string;
    exposure?: number;
    addr1?: string;
    domain?: string;
    [key: string]: unknown;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: 'OWNS' | 'MADE' | 'FROM_DEVICE' | 'BILLED_IN' | 'PURCHASER_EMAIL' | 'SHARED_WITH' | 'PRIOR_CASE_ON' | 'INVESTIGATES' | 'RAISED_FOR' | 'RECALLS_MEMORY' | string;
  label?: string;
}

export interface SubgraphResponse {
  case_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    node_count: number;
    edge_count: number;
  };
}

export interface ActionApprovalRecord {
  auth_code: string;
  case_id: string;
  action: string;
  route: string;
  approver: string;
  notes: string;
  timestamp: string;
  status: string;
  message: string;
}
