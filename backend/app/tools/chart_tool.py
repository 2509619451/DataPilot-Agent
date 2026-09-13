from pathlib import Path
from uuid import uuid4
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

from app.core.config import get_settings


settings = get_settings()


# ============================================================
# Matplotlib 中文字体配置
# ============================================================

def configure_matplotlib_font():
    """
    自动寻找系统中可用的中文字体。

    Docker / Linux:
        优先使用 Noto Sans CJK SC

    Windows:
        可以使用 Microsoft YaHei / SimHei

    macOS:
        可以使用 PingFang SC
    """

    candidates = [
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
    ]

    # 获取 Matplotlib 当前识别到的所有字体
    installed_fonts = {
        font.name
        for font in font_manager.fontManager.ttflist
    }

    selected_font = None

    for font_name in candidates:
        if font_name in installed_fonts:
            selected_font = font_name
            break

    if selected_font:
        matplotlib.rcParams["font.sans-serif"] = [
            selected_font,
            "DejaVu Sans",
        ]

        print(
            f"[Matplotlib] 使用中文字体: {selected_font}"
        )

    else:
        print(
            "[Matplotlib] WARNING: "
            "未检测到中文字体，中文可能显示为方框"
        )

    # 防止负号显示成方块
    matplotlib.rcParams["axes.unicode_minus"] = False


# 程序启动时执行一次
configure_matplotlib_font()


# ============================================================
# 自动解析图表字段
# ============================================================

def _resolve_axes(
    df: pd.DataFrame,
    x: str | None,
    y: str | None,
) -> tuple[str, str]:

    """
    根据实际 records 自动选择 x / y 字段。

    V4 修复：
    不再硬编码 total_sales / total_profit。
    """

    cols = list(df.columns)

    if not cols:
        raise ValueError("图表数据没有字段")

    # --------------------------------------------------------
    # 自动寻找 X 轴
    # --------------------------------------------------------

    if x not in cols:

        x = next(
            (
                c
                for c in cols
                if not pd.api.types.is_numeric_dtype(df[c])
            ),
            cols[0],
        )

    # --------------------------------------------------------
    # 自动寻找 Y 轴
    # --------------------------------------------------------

    if y not in cols or y == x:

        numeric = [
            c
            for c in cols
            if c != x
            and pd.api.types.is_numeric_dtype(df[c])
        ]

        # 如果 Pandas 没识别成 numeric，
        # 再尝试手动转换
        if not numeric:

            for c in cols:

                if c == x:
                    continue

                converted = pd.to_numeric(
                    df[c],
                    errors="coerce",
                )

                if converted.notna().any():

                    df[c] = converted
                    numeric.append(c)
                    break

        if not numeric:

            raise ValueError(
                f"找不到数值 y 轴，实际字段: {cols}"
            )

        y = numeric[0]

    return x, y


# ============================================================
# 创建图表
# ============================================================

def create_chart_from_records(
    records: list[dict[str, Any]],
    chart_type: str = "bar",
    x: str | None = None,
    y: str | None = None,
    title: str = "数据分析图表",
) -> dict:

    if not records:

        raise ValueError(
            "没有可绘图的数据"
        )

    # --------------------------------------------------------
    # 转换数据
    # --------------------------------------------------------

    df = pd.DataFrame(records)

    x, y = _resolve_axes(
        df,
        x,
        y,
    )

    # --------------------------------------------------------
    # 创建画布
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(9, 5.4)
    )

    chart_type = chart_type.lower()

    # ========================================================
    # 折线图
    # ========================================================

    if chart_type == "line":

        ax.plot(
            df[x].astype(str),
            pd.to_numeric(
                df[y],
                errors="coerce",
            ),
            marker="o",
        )

        ax.tick_params(
            axis="x",
            rotation=35,
        )

    # ========================================================
    # 饼图
    # ========================================================

    elif chart_type == "pie":

        values = pd.to_numeric(
            df[y],
            errors="coerce",
        ).fillna(0)

        # 饼图不能出现负数，
        # 如果数据不适合绘制饼图，
        # 自动降级为柱状图
        if (
            (values < 0).any()
            or values.sum() <= 0
        ):

            chart_type = "bar"

            ax.bar(
                df[x].astype(str),
                values,
            )

            ax.tick_params(
                axis="x",
                rotation=35,
            )

        else:

            ax.pie(
                values,
                labels=df[x].astype(str),
                autopct="%1.1f%%",
                startangle=90,
            )

            ax.set_ylabel("")

    # ========================================================
    # 散点图
    # ========================================================

    elif chart_type == "scatter":

        ax.scatter(
            pd.to_numeric(
                df[x],
                errors="coerce",
            ),
            pd.to_numeric(
                df[y],
                errors="coerce",
            ),
        )

    # ========================================================
    # 柱状图
    # ========================================================

    else:

        chart_type = "bar"

        ax.bar(
            df[x].astype(str),
            pd.to_numeric(
                df[y],
                errors="coerce",
            ),
        )

        ax.tick_params(
            axis="x",
            rotation=35,
        )

    # ========================================================
    # 标题
    # ========================================================

    ax.set_title(
        title,
        fontsize=15,
        pad=16,
    )

    # ========================================================
    # 坐标轴
    # ========================================================

    if chart_type != "pie":

        ax.set_xlabel(x)
        ax.set_ylabel(y)

    # ========================================================
    # 保存
    # ========================================================

    fig.tight_layout()

    chart_id = str(
        uuid4()
    )

    path = (
        Path(settings.chart_dir)
        / f"{chart_id}.png"
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    return {
        "id": chart_id,
        "path": str(path),
        "chart_type": chart_type,
        "title": title,
        "x": x,
        "y": y,
    }