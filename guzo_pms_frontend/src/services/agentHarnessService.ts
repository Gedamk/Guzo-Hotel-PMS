import { http } from "./http";

export type AgentHarnessTaskName =
  | "create_reservation_request"
  | "suggest_room_assignment"
  | "create_housekeeping_task"
  | "explain_check_in_blocked"
  | "summarize_front_desk_issues"
  | "summarize_manager_alerts";

export type AgentHarnessResponse = {
  status: string;
  message: string;
  task_name: AgentHarnessTaskName;
  data: Record<string, unknown>;
};

export async function runAgentHarnessTask(
  taskName: AgentHarnessTaskName,
  data: Record<string, unknown>,
  propertyCode: string
): Promise<AgentHarnessResponse> {
  const response = await http.post<AgentHarnessResponse>("/agent-harness/tasks", {
    task_name: taskName,
    property_code: propertyCode,
    data,
  });
  return response.data;
}
