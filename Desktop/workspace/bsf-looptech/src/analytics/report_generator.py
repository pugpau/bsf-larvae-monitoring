"""
レポート生成機能
定期レポート、データエクスポート、分析レポートを自動生成
"""

import logging
import json
import csv
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field
from io import StringIO, BytesIO

from src.analytics.aggregation import DataAggregationService, DataQuality
from src.analytics.trend_analysis import TrendAnalysisEngine, TrendType
from src.analytics.statistics import statistical_analyzer
from src.analytics.anomaly_detector import anomaly_detector
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ReportFormat(str, Enum):
    """レポート形式"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"
    EXCEL = "excel"


class ReportType(str, Enum):
    """レポートの種類"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_ANALYSIS = "weekly_analysis"
    MONTHLY_REPORT = "monthly_report"
    QUALITY_ASSESSMENT = "quality_assessment"
    ANOMALY_REPORT = "anomaly_report"
    TREND_ANALYSIS = "trend_analysis"
    CUSTOM = "custom"


class ReportSchedule(str, Enum):
    """レポートスケジュール"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class ReportConfig(BaseModel):
    """レポート設定"""
    report_type: ReportType
    format: ReportFormat
    schedule: ReportSchedule
    farm_id: Optional[str] = None
    device_ids: Optional[List[str]] = None
    measurement_types: List[str] = Field(..., description="対象測定タイプ")
    include_quality_metrics: bool = Field(default=True)
    include_anomalies: bool = Field(default=True)
    include_trends: bool = Field(default=True)
    custom_filters: Optional[Dict[str, Any]] = None
    recipients: Optional[List[str]] = None  # 将来のメール送信用


class ReportSection(BaseModel):
    """レポートセクション"""
    title: str
    content: Dict[str, Any]
    charts: Optional[List[Dict[str, Any]]] = None
    tables: Optional[List[Dict[str, Any]]] = None


class GeneratedReport(BaseModel):
    """生成されたレポート"""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    generated_at: datetime
    time_range: Dict[str, datetime]
    farm_id: Optional[str]
    sections: List[ReportSection]
    summary: Dict[str, Any]
    file_path: Optional[str] = None
    file_size: Optional[int] = None


class ReportGeneratorService:
    """レポート生成サービス"""
    
    def __init__(self):
        self.aggregation_service = DataAggregationService()
        self.trend_engine = TrendAnalysisEngine()
        self.reports_dir = Path("/tmp/bsf_reports")  # 本番環境では適切なパスに変更
        self.reports_dir.mkdir(exist_ok=True)
    
    async def generate_report(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> GeneratedReport:
        """
        レポートを生成
        """
        try:
            report_id = f"{config.report_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"Generating report: {report_id}")
            
            # レポートタイプに応じてセクションを生成
            sections = []
            
            if config.report_type == ReportType.DAILY_SUMMARY:
                sections = await self._generate_daily_summary_sections(
                    config, start_time, end_time
                )
            elif config.report_type == ReportType.WEEKLY_ANALYSIS:
                sections = await self._generate_weekly_analysis_sections(
                    config, start_time, end_time
                )
            elif config.report_type == ReportType.QUALITY_ASSESSMENT:
                sections = await self._generate_quality_assessment_sections(
                    config, start_time, end_time
                )
            elif config.report_type == ReportType.ANOMALY_REPORT:
                sections = await self._generate_anomaly_report_sections(
                    config, start_time, end_time
                )
            elif config.report_type == ReportType.TREND_ANALYSIS:
                sections = await self._generate_trend_analysis_sections(
                    config, start_time, end_time
                )
            else:
                sections = await self._generate_custom_sections(
                    config, start_time, end_time
                )
            
            # サマリーを作成
            summary = await self._create_report_summary(sections, config)
            
            # レポートオブジェクトを作成
            report = GeneratedReport(
                report_id=report_id,
                report_type=config.report_type,
                format=config.format,
                generated_at=datetime.now(timezone.utc),
                time_range={"start": start_time, "end": end_time},
                farm_id=config.farm_id,
                sections=sections,
                summary=summary
            )
            
            # ファイルに出力
            if config.format != ReportFormat.JSON:
                file_path = await self._export_report_to_file(report, config.format)
                report.file_path = file_path
                if file_path and Path(file_path).exists():
                    report.file_size = Path(file_path).stat().st_size
            
            logger.info(f"Report generated successfully: {report_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    async def _generate_daily_summary_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """日次サマリーセクションを生成"""
        sections = []
        
        # 概要セクション
        overview_content = {
            "report_period": f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
            "farm_id": config.farm_id,
            "measurement_types": config.measurement_types
        }
        sections.append(ReportSection(
            title="Overview",
            content=overview_content
        ))
        
        # 各測定タイプの統計
        for measurement_type in config.measurement_types:
            try:
                # 統計サマリーを取得
                summary = await statistical_analyzer.get_statistical_summary(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    farm_id=config.farm_id
                )
                
                if summary:
                    content = {
                        "measurement_type": measurement_type,
                        "statistics": {
                            "mean": summary.mean,
                            "min": summary.min_value,
                            "max": summary.max_value,
                            "std_dev": summary.std_dev,
                            "data_points": summary.data_points
                        },
                        "quality_score": summary.quality_score,
                        "trend_direction": summary.trend_direction,
                        "trend_strength": summary.trend_strength
                    }
                    
                    sections.append(ReportSection(
                        title=f"{measurement_type.title()} Statistics",
                        content=content
                    ))
            except Exception as e:
                logger.error(f"Error generating statistics for {measurement_type}: {e}")
        
        # データ品質セクション
        if config.include_quality_metrics:
            quality_section = await self._generate_quality_section(
                config.measurement_types, start_time, end_time, config.farm_id
            )
            sections.append(quality_section)
        
        # 異常検知セクション
        if config.include_anomalies:
            anomaly_section = await self._generate_anomaly_section(
                start_time, end_time, config.farm_id
            )
            sections.append(anomaly_section)
        
        return sections
    
    async def _generate_weekly_analysis_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """週次分析セクションを生成"""
        sections = []
        
        # 週間概要
        overview_content = {
            "report_period": f"Week of {start_time.strftime('%Y-%m-%d')}",
            "farm_id": config.farm_id,
            "total_days": (end_time - start_time).days,
            "measurement_types": config.measurement_types
        }
        sections.append(ReportSection(
            title="Weekly Overview",
            content=overview_content
        ))
        
        # トレンド分析（有効な場合）
        if config.include_trends:
            for measurement_type in config.measurement_types:
                try:
                    trend_result = await self.trend_engine.analyze_trend(
                        measurement_type=measurement_type,
                        start_time=start_time,
                        end_time=end_time,
                        farm_id=config.farm_id
                    )
                    
                    content = {
                        "measurement_type": measurement_type,
                        "trend_direction": trend_result.trend_direction,
                        "trend_strength": trend_result.trend_strength,
                        "slope": trend_result.slope,
                        "r_squared": trend_result.r_squared,
                        "forecast": trend_result.next_period_forecast
                    }
                    
                    sections.append(ReportSection(
                        title=f"{measurement_type.title()} Trend Analysis",
                        content=content
                    ))
                except Exception as e:
                    logger.error(f"Error generating trend analysis for {measurement_type}: {e}")
        
        # 比較分析（前週との比較）
        comparison_section = await self._generate_comparison_section(
            config.measurement_types, start_time, end_time, config.farm_id
        )
        sections.append(comparison_section)
        
        return sections
    
    async def _generate_quality_assessment_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """品質評価セクションを生成"""
        sections = []
        
        for measurement_type in config.measurement_types:
            try:
                quality = await self.aggregation_service.evaluate_data_quality(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    farm_id=config.farm_id
                )
                
                content = {
                    "measurement_type": measurement_type,
                    "overall_score": quality.overall_score,
                    "completeness": quality.completeness,
                    "consistency": quality.consistency,
                    "accuracy": quality.accuracy,
                    "timeliness": quality.timeliness,
                    "metrics": {
                        "missing_data_rate": quality.missing_data_rate,
                        "outlier_rate": quality.outlier_rate,
                        "duplicate_rate": quality.duplicate_rate,
                        "data_freshness_hours": quality.data_freshness_hours
                    },
                    "data_points": {
                        "total": quality.total_points,
                        "valid": quality.valid_points,
                        "missing": quality.missing_points,
                        "outliers": quality.outlier_points
                    }
                }
                
                sections.append(ReportSection(
                    title=f"{measurement_type.title()} Quality Assessment",
                    content=content
                ))
                
            except Exception as e:
                logger.error(f"Error generating quality assessment for {measurement_type}: {e}")
        
        return sections
    
    async def _generate_anomaly_report_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """異常レポートセクションを生成"""
        sections = []
        
        try:
            # アクティブな異常を取得
            active_anomalies = anomaly_detector.get_active_anomalies()
            
            content = {
                "report_period": f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
                "total_active_anomalies": len(active_anomalies),
                "anomalies_by_severity": {},
                "anomalies_by_type": {},
                "anomaly_details": []
            }
            
            # 異常を分類
            for anomaly in active_anomalies:
                # 重要度別
                severity = anomaly.severity.value
                content["anomalies_by_severity"][severity] = content["anomalies_by_severity"].get(severity, 0) + 1
                
                # 測定タイプ別
                measurement_type = anomaly.measurement_type
                content["anomalies_by_type"][measurement_type] = content["anomalies_by_type"].get(measurement_type, 0) + 1
                
                # 詳細情報
                content["anomaly_details"].append({
                    "id": str(anomaly.id),
                    "measurement_type": anomaly.measurement_type,
                    "severity": severity,
                    "detected_at": anomaly.detected_at.isoformat(),
                    "value": anomaly.actual_value,
                    "threshold": anomaly.threshold_value,
                    "status": anomaly.status.value
                })
            
            sections.append(ReportSection(
                title="Anomaly Detection Report",
                content=content
            ))
            
        except Exception as e:
            logger.error(f"Error generating anomaly report: {e}")
        
        return sections
    
    async def _generate_trend_analysis_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """トレンド分析セクションを生成"""
        sections = []
        
        for measurement_type in config.measurement_types:
            try:
                # 線形トレンド分析
                linear_trend = await self.trend_engine.analyze_trend(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    trend_type=TrendType.LINEAR,
                    farm_id=config.farm_id
                )
                
                # 季節性分析
                seasonal_trend = await self.trend_engine.analyze_trend(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    trend_type=TrendType.SEASONAL,
                    farm_id=config.farm_id
                )
                
                # 変化点検出
                change_points = await self.trend_engine.detect_change_points(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    farm_id=config.farm_id
                )
                
                content = {
                    "measurement_type": measurement_type,
                    "linear_trend": {
                        "direction": linear_trend.trend_direction,
                        "strength": linear_trend.trend_strength,
                        "slope": linear_trend.slope,
                        "r_squared": linear_trend.r_squared
                    },
                    "seasonality": {
                        "detected": seasonal_trend.seasonality_detected,
                        "period": seasonal_trend.seasonal_period,
                        "strength": seasonal_trend.seasonal_strength
                    },
                    "change_points": [
                        {
                            "timestamp": cp.timestamp.isoformat(),
                            "magnitude": cp.change_magnitude,
                            "confidence": cp.confidence,
                            "type": cp.change_type
                        }
                        for cp in change_points
                    ]
                }
                
                sections.append(ReportSection(
                    title=f"{measurement_type.title()} Trend Analysis",
                    content=content
                ))
                
            except Exception as e:
                logger.error(f"Error generating trend analysis for {measurement_type}: {e}")
        
        return sections
    
    async def _generate_custom_sections(
        self,
        config: ReportConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[ReportSection]:
        """カスタムセクションを生成"""
        # 基本的な統計情報を含むカスタムレポート
        return await self._generate_daily_summary_sections(config, start_time, end_time)
    
    async def _generate_quality_section(
        self,
        measurement_types: List[str],
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str]
    ) -> ReportSection:
        """データ品質セクションを生成"""
        quality_summary = {
            "overall_quality": 0.0,
            "measurement_quality": {}
        }
        
        total_score = 0.0
        valid_measurements = 0
        
        for measurement_type in measurement_types:
            try:
                quality = await self.aggregation_service.evaluate_data_quality(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    farm_id=farm_id
                )
                
                quality_summary["measurement_quality"][measurement_type] = {
                    "overall_score": quality.overall_score,
                    "completeness": quality.completeness,
                    "accuracy": quality.accuracy,
                    "missing_rate": quality.missing_data_rate
                }
                
                total_score += quality.overall_score
                valid_measurements += 1
                
            except Exception as e:
                logger.error(f"Error evaluating quality for {measurement_type}: {e}")
        
        if valid_measurements > 0:
            quality_summary["overall_quality"] = total_score / valid_measurements
        
        return ReportSection(
            title="Data Quality Assessment",
            content=quality_summary
        )
    
    async def _generate_anomaly_section(
        self,
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str]
    ) -> ReportSection:
        """異常検知セクションを生成"""
        try:
            active_anomalies = anomaly_detector.get_active_anomalies()
            
            # 期間内の異常をフィルタ
            period_anomalies = [
                anomaly for anomaly in active_anomalies
                if start_time <= anomaly.detected_at <= end_time
            ]
            
            if farm_id:
                period_anomalies = [
                    anomaly for anomaly in period_anomalies
                    if anomaly.farm_id == farm_id
                ]
            
            content = {
                "total_anomalies": len(period_anomalies),
                "severity_breakdown": {},
                "recent_anomalies": []
            }
            
            # 重要度別分類
            for anomaly in period_anomalies:
                severity = anomaly.severity.value
                content["severity_breakdown"][severity] = content["severity_breakdown"].get(severity, 0) + 1
            
            # 最新の異常（最大5件）
            recent_anomalies = sorted(period_anomalies, key=lambda x: x.detected_at, reverse=True)[:5]
            for anomaly in recent_anomalies:
                content["recent_anomalies"].append({
                    "measurement_type": anomaly.measurement_type,
                    "severity": anomaly.severity.value,
                    "detected_at": anomaly.detected_at.isoformat(),
                    "description": f"Value {anomaly.actual_value} exceeded threshold {anomaly.threshold_value}"
                })
            
            return ReportSection(
                title="Anomaly Detection Summary",
                content=content
            )
            
        except Exception as e:
            logger.error(f"Error generating anomaly section: {e}")
            return ReportSection(
                title="Anomaly Detection Summary",
                content={"error": "Failed to generate anomaly summary"}
            )
    
    async def _generate_comparison_section(
        self,
        measurement_types: List[str],
        current_start: datetime,
        current_end: datetime,
        farm_id: Optional[str]
    ) -> ReportSection:
        """比較分析セクションを生成"""
        # 前期間（同じ長さ）のデータと比較
        duration = current_end - current_start
        previous_start = current_start - duration
        previous_end = current_start
        
        comparisons = {}
        
        for measurement_type in measurement_types:
            try:
                # 現在期間の統計
                current_summary = await statistical_analyzer.get_statistical_summary(
                    measurement_type=measurement_type,
                    start_time=current_start,
                    end_time=current_end,
                    farm_id=farm_id
                )
                
                # 前期間の統計
                previous_summary = await statistical_analyzer.get_statistical_summary(
                    measurement_type=measurement_type,
                    start_time=previous_start,
                    end_time=previous_end,
                    farm_id=farm_id
                )
                
                if current_summary and previous_summary:
                    # 変化率を計算
                    mean_change = ((current_summary.mean - previous_summary.mean) / previous_summary.mean) * 100
                    max_change = ((current_summary.max_value - previous_summary.max_value) / previous_summary.max_value) * 100
                    
                    comparisons[measurement_type] = {
                        "current_mean": current_summary.mean,
                        "previous_mean": previous_summary.mean,
                        "mean_change_percent": mean_change,
                        "current_max": current_summary.max_value,
                        "previous_max": previous_summary.max_value,
                        "max_change_percent": max_change,
                        "trend_change": f"{previous_summary.trend_direction} → {current_summary.trend_direction}"
                    }
                
            except Exception as e:
                logger.error(f"Error generating comparison for {measurement_type}: {e}")
        
        return ReportSection(
            title="Period Comparison Analysis",
            content={
                "comparison_period": f"{previous_start.strftime('%Y-%m-%d')} to {previous_end.strftime('%Y-%m-%d')}",
                "current_period": f"{current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}",
                "comparisons": comparisons
            }
        )
    
    async def _create_report_summary(
        self,
        sections: List[ReportSection],
        config: ReportConfig
    ) -> Dict[str, Any]:
        """レポートサマリーを作成"""
        summary = {
            "total_sections": len(sections),
            "report_type": config.report_type.value,
            "measurement_types": config.measurement_types,
            "farm_id": config.farm_id,
            "includes_quality": config.include_quality_metrics,
            "includes_anomalies": config.include_anomalies,
            "includes_trends": config.include_trends
        }
        
        # 各セクションからキーメトリクスを抽出
        key_metrics = {}
        for section in sections:
            if "Statistics" in section.title:
                measurement_type = section.content.get("measurement_type")
                if measurement_type:
                    stats = section.content.get("statistics", {})
                    key_metrics[measurement_type] = {
                        "mean": stats.get("mean"),
                        "quality_score": section.content.get("quality_score"),
                        "trend": section.content.get("trend_direction")
                    }
        
        summary["key_metrics"] = key_metrics
        return summary
    
    async def _export_report_to_file(
        self,
        report: GeneratedReport,
        format: ReportFormat
    ) -> str:
        """レポートをファイルにエクスポート"""
        try:
            filename = f"{report.report_id}.{format.value}"
            file_path = self.reports_dir / filename
            
            if format == ReportFormat.JSON:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Pydanticモデルを辞書に変換してからJSON化
                    report_dict = report.model_dump()
                    # datetimeをISO文字列に変換
                    def convert_datetime(obj):
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        elif isinstance(obj, dict):
                            return {k: convert_datetime(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_datetime(item) for item in obj]
                        return obj
                    
                    report_dict = convert_datetime(report_dict)
                    json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            elif format == ReportFormat.CSV:
                # CSVの場合、フラットなデータ構造に変換
                await self._export_to_csv(report, file_path)
            
            elif format == ReportFormat.HTML:
                await self._export_to_html(report, file_path)
            
            else:
                # その他の形式は未実装
                logger.warning(f"Export format {format} not implemented")
                return None
            
            logger.info(f"Report exported to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error exporting report to file: {e}")
            raise
    
    async def _export_to_csv(self, report: GeneratedReport, file_path: Path):
        """CSV形式でエクスポート"""
        rows = []
        
        for section in report.sections:
            section_data = {
                "section": section.title,
                "report_id": report.report_id,
                "generated_at": report.generated_at.isoformat(),
                "farm_id": report.farm_id
            }
            
            # セクション内容をフラット化
            def flatten_dict(d, parent_key='', sep='_'):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, v))
                return dict(items)
            
            flattened_content = flatten_dict(section.content)
            section_data.update(flattened_content)
            rows.append(section_data)
        
        # DataFrameに変換してCSV出力
        df = pd.DataFrame(rows)
        df.to_csv(file_path, index=False, encoding='utf-8')
    
    async def _export_to_html(self, report: GeneratedReport, file_path: Path):
        """HTML形式でエクスポート"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report.report_type.value} Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #4CAF50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report.report_type.value.replace('_', ' ').title()} Report</h1>
                <p>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p>Period: {report.time_range['start'].strftime('%Y-%m-%d')} to {report.time_range['end'].strftime('%Y-%m-%d')}</p>
                {f"<p>Farm ID: {report.farm_id}</p>" if report.farm_id else ""}
            </div>
        """
        
        # 各セクションをHTML化
        for section in report.sections:
            html_content += f"""
            <div class="section">
                <h2>{section.title}</h2>
            """
            
            # セクション内容をHTMLテーブルとして表示
            if isinstance(section.content, dict):
                html_content += self._dict_to_html_table(section.content)
            
            html_content += "</div>"
        
        html_content += """
        </body>
        </html>
        """
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _dict_to_html_table(self, data: Dict[str, Any], max_depth: int = 2, current_depth: int = 0) -> str:
        """辞書をHTMLテーブルに変換"""
        if current_depth >= max_depth:
            return f"<p>{str(data)}</p>"
        
        html = "<table>"
        for key, value in data.items():
            html += f"<tr><th>{key}</th>"
            if isinstance(value, dict) and current_depth < max_depth - 1:
                html += f"<td>{self._dict_to_html_table(value, max_depth, current_depth + 1)}</td>"
            elif isinstance(value, list):
                html += f"<td><ul>"
                for item in value[:10]:  # 最大10項目まで表示
                    html += f"<li>{str(item)}</li>"
                if len(value) > 10:
                    html += f"<li>... and {len(value) - 10} more items</li>"
                html += "</ul></td>"
            else:
                html += f"<td>{str(value)}</td>"
            html += "</tr>"
        html += "</table>"
        return html


# グローバルインスタンス
report_generator = ReportGeneratorService()