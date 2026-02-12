"""Seed initial BSF knowledge into the knowledge base."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.rag.embedding import get_embedding
from src.rag.knowledge_repo import create_knowledge
from src.rag.schemas import KnowledgeCreate

logger = logging.getLogger(__name__)

# Pre-defined BSF domain knowledge
SEED_DATA: list[dict] = [
    {
        "title": "BSF幼虫の最適飼育温度",
        "content": (
            "ブラックソルジャーフライ（BSF）の幼虫飼育における最適温度は27-30℃です。"
            "25℃以下では成長が遅延し、35℃以上では死亡率が上昇します。"
            "湿度は60-70%RHが推奨されます。"
            "日本の冬季（12-2月）は加温設備が必須となります。"
        ),
        "source_type": "manual",
    },
    {
        "title": "基材配合の基本原則",
        "content": (
            "BSF幼虫の基材配合では、C/N比（炭素/窒素比）が15-25の範囲が最適です。"
            "水分含有率は60-70%を維持する必要があります。"
            "pHは6.0-8.0の範囲が適切で、極端な酸性・アルカリ性は避けます。"
            "有機物含有量が高いほど幼虫の成長速度が向上しますが、"
            "過剰な油脂分（10%以上）は発酵異常を引き起こす可能性があります。"
        ),
        "source_type": "manual",
    },
    {
        "title": "固化処理の基準と方法",
        "content": (
            "産業廃棄物の固化処理では、セメント系固化材が最も一般的です。"
            "普通ポルトランドセメントの添加量は廃棄物1トンあたり100-300kgが目安です。"
            "溶出試験基準は土壌汚染対策法に準拠し、鉛0.01mg/L以下、"
            "砒素0.01mg/L以下、カドミウム0.003mg/L以下などの基準値があります。"
            "六価クロムの基準値は0.05mg/L以下です。"
        ),
        "source_type": "manual",
    },
    {
        "title": "溶出抑制剤の選定",
        "content": (
            "重金属の溶出を抑制するためにキレート剤や無機系吸着材を使用します。"
            "キレート剤は鉛やカドミウムに対して効果的で、添加量は1-5kg/tが一般的です。"
            "無機系吸着材（ゼオライト等）は広範囲の重金属に対応可能ですが、"
            "添加量が多く必要（10-50kg/t）でコストが高くなる傾向があります。"
            "pH調整（アルカリ側）も溶出抑制に有効ですが、六価クロムはpH上昇で溶出が増加するため注意が必要です。"
        ),
        "source_type": "manual",
    },
    {
        "title": "BSF処理残渣の品質管理",
        "content": (
            "BSF幼虫処理後の残渣は堆肥として利用可能ですが、品質管理が重要です。"
            "残渣のC/N比は10-15程度まで低下していることが望ましいです。"
            "重金属含有量は肥料取締法の基準値以下である必要があります。"
            "水分含有率は30-40%に調整して出荷します。"
            "病原性微生物の不検出を確認するため、定期的な衛生検査を実施します。"
        ),
        "source_type": "manual",
    },
]


async def seed_knowledge(session: AsyncSession) -> int:
    """Insert seed knowledge records. Returns count of records created."""
    count = 0
    for item in SEED_DATA:
        data = KnowledgeCreate(
            title=item["title"],
            content=item["content"],
            source_type=item["source_type"],
        )
        embedding = await get_embedding(item["content"])
        await create_knowledge(session, data, embedding=embedding)
        count += 1
        logger.info("Seeded knowledge: %s", item["title"])

    return count
