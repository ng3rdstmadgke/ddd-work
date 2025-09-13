from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Any

class Color(BaseModel):
    red: int = Field(default=0)  # default値を設定
    green: int = Field(default=0)
    blue: int = Field(default=0)
    model_config = ConfigDict(frozen=True)

    # 属性のバリデーション
    @field_validator('red', 'green', 'blue')
    @classmethod
    def check_rgb_range(cls, v: Any, field):
        if not (0 <= v <= 255):
            raise ValueError(f"{field.field_name} must be between 0 and 255")
        return v

    # 値オブジェクトの振る舞いを定義するメソッド
    def min_with(self, color: "Color") -> "Color":
        return Color(
            red=min(self.red, color.red),
            green=min(self.green, color.green),
            blue=min(self.blue, color.blue)
        )
        

if __name__ == "__main__":
    color_1 = Color(red=255, green=0, blue=0)
    color_2 = Color(red=1, green=1, blue=1)
    print(color_1.min_with(color_2))  # Color(red=1, green=0, blue=0)