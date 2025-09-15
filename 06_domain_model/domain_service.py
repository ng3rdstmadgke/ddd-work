from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta
from typing import Any

class UserId(BaseModel):
    pass

class Priority(BaseModel):
    pass

class DepartmentPolicy(BaseModel):
    escalation_factor: float
    max_agent_proc_time: timedelta

    def get_max_response_time_for(self, priority: Priority) -> timedelta:
        return timedelta(hours=1)


##################################
# リポジトリ 
##################################

class DepartmentRepository(BaseModel):
    def get_department_policy(self, agent_id: UserId) -> DepartmentPolicy:
        return DepartmentPolicy(escalation_factor=1.5, max_agent_proc_time=timedelta(hours=8))

    def get_upcoming_shifts(self, agent_id: UserId, start_time: datetime, end_time: datetime) -> Any:
        pass

####################################
# ドメインサービス
####################################
class ResponseTimeFrameCalculationService(BaseModel):
    department_repository: DepartmentRepository
    model_config = ConfigDict(frozen=True)

    # 担当者のチケットの対応期限を計算するドメインサービス
    # 期限は、チケットの優先度、エスカレーション状態、担当者の勤務シフトに基づいて計算される
    def calculate_agent_response_deadline(
        self,
        agent_id: UserId,
        priority: Priority,
        escalated: bool,
        start_time: datetime,
    ):
        policy = self.department_repository.get_department_policy(agent_id)

        # 優先度に基づいて最大対応時間を取得
        max_proc_time = policy.get_max_response_time_for(priority)

        # エスカレーションされている場合、最大対応時間をエスカレーション係数で調整
        if (escalated):
            max_proc_time = max_proc_time * policy.escalation_factor

        # 担当者の勤務シフトを取得
        shifts = self.department_repository.get_upcoming_shifts(
            agent_id,
            start_time,
            start_time + policy.max_agent_proc_time
        )

        # シフトに基づいて対応期限を計算するロジック
        return calculate_target_time(max_proc_time, shifts)