import type { AgentType } from "@/lib/types";

export interface AgentDisplayConfig {
  agentType: AgentType;
  displayName: string;
  group: "workflow" | "shared";
  workflowLabel: string;
  usedBy: string;
  description: string;
}

export const agentDisplayConfigs: AgentDisplayConfig[] = [
  {
    agentType: "analyst",
    displayName: "Sales Analyst",
    group: "workflow",
    workflowLabel: "Sales",
    usedBy: "Used in Sales workflow",
    description: "Extracts sales findings, risks, opportunities, and recommendations.",
  },
  {
    agentType: "classifier",
    displayName: "Feedback Classifier",
    group: "workflow",
    workflowLabel: "Customer Feedback",
    usedBy: "Used in Customer Feedback workflow",
    description: "Classifies customer comments into themes, sentiment, and evidence.",
  },
  {
    agentType: "insight",
    displayName: "Insight Agent",
    group: "workflow",
    workflowLabel: "Customer Feedback",
    usedBy: "Used in Customer Feedback workflow",
    description: "Turns classified feedback into product insights and recommendations.",
  },
  {
    agentType: "timeline",
    displayName: "Incident Timeline",
    group: "workflow",
    workflowLabel: "Incident",
    usedBy: "Used in Incident workflow",
    description: "Extracts timestamped incident events with source evidence.",
  },
  {
    agentType: "root_cause",
    displayName: "Root Cause Agent",
    group: "workflow",
    workflowLabel: "Incident",
    usedBy: "Used in Incident workflow",
    description: "Separates confirmed facts, likely causes, unknowns, and follow-ups.",
  },
  {
    agentType: "router",
    displayName: "Router",
    group: "shared",
    workflowLabel: "Intake",
    usedBy: "Used before workflow creation for auto-detection",
    description: "Detects whether an input should run as sales, feedback, or incident.",
  },
  {
    agentType: "reviewer",
    displayName: "Reviewer",
    group: "shared",
    workflowLabel: "Shared Governance",
    usedBy: "Shared by Sales, Customer Feedback, and Incident",
    description: "Checks factual support before human approval.",
  },
  {
    agentType: "writer",
    displayName: "Writer",
    group: "shared",
    workflowLabel: "Shared Governance",
    usedBy: "Shared by Sales, Customer Feedback, and Incident",
    description: "Creates the final report from reviewed, human-approved analysis.",
  },
];

export const agentDisplayByType = new Map(
  agentDisplayConfigs.map((config) => [config.agentType, config]),
);

export function getAgentDisplay(agentType: AgentType): AgentDisplayConfig {
  return agentDisplayByType.get(agentType) ?? {
    agentType,
    displayName: agentType,
    group: "shared",
    workflowLabel: "Shared",
    usedBy: "Used by configured workflows",
    description: "Configured workflow agent.",
  };
}
