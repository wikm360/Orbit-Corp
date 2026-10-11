# Schema `CMMS3` — جدول‌های دارای داده

(تولید خودکار از دیتابیس ریستور‌شده؛ فقط جدول‌های با ردیف > 0. ستون «enum» مقادیر Lookup را نشان می‌دهد.)

| جدول | ردیف | ستون | وضعیت | توضیح |
|---|---:|---:|---|---|
| [RCMDecisionLogic](#rcmdecisionlogic) | 1 | 6 | 🔴 استفاده‌نشده (seed) |  |
| [RCMDecisionLogicNode](#rcmdecisionlogicnode) | 19 | 10 | 🔴 استفاده‌نشده (seed) |  |
| [Recommendation](#recommendation) | 1 | 5 | 🔴 استفاده‌نشده (seed) |  |
| [RecommendationType](#recommendationtype) | 4 | 6 | 🔴 استفاده‌نشده (seed) |  |

## RCMDecisionLogic

`CMMS3.RCMDecisionLogic` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RCMDecisionLogicID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Title | nvarchar(256) |  |  |  |
| Description | nvarchar(512) | Y |  |  |
| RecommendationRef | bigint |  | → CMMS3.Recommendation.RecommendationID |  |

ارجاع‌شده توسط: `CMMS3.RCMEvaluation`، `CMMS3.RCMDecisionLogicNode`

## RCMDecisionLogicNode

`CMMS3.RCMDecisionLogicNode` — 19 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RCMDecisionLogicNodeID | bigint |  | PK |  |
| RCMIdentifier | nvarchar(64) | Y |  |  |
| Prompt | nvarchar(256) | Y |  |  |
| RCMDecisionLogicNodeYesRef | bigint | Y | → CMMS3.RCMDecisionLogicNode.RCMDecisionLogicNodeID |  |
| RCMDecisionLogicNodeNoRef | bigint | Y | → CMMS3.RCMDecisionLogicNode.RCMDecisionLogicNodeID |  |
| RCMDecisionLogicRef | bigint |  | → CMMS3.RCMDecisionLogic.RCMDecisionLogicID |  |
| RecommendationTypeYesRef | bigint | Y | → CMMS3.RecommendationType.RecommendationTypeID |  |
| RecommendationTypeNoRef | bigint | Y | → CMMS3.RecommendationType.RecommendationTypeID |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `CMMS3.RCMDecisionLogicAssessment`، `CMMS3.RCMDecisionLogicNode`، `CMMS3.RCMDecisionLogicNodeNote`

## Recommendation

`CMMS3.Recommendation` — 1 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RecommendationID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `CMMS3.RCMDecisionLogic`، `CMMS3.RecommendationType`

## RecommendationType

`CMMS3.RecommendationType` — 4 rows — 🔴 استفاده‌نشده (seed)

| ستون | نوع | null | کلید/ارجاع | enum |
|---|---|:-:|---|---|
| RecommendationTypeID | bigint |  | PK |  |
| Number | nvarchar(64) |  |  |  |
| Title | nvarchar(128) |  |  |  |
| RecommendationRef | bigint |  | → CMMS3.Recommendation.RecommendationID |  |
| Description | nvarchar(512) | Y |  |  |

ارجاع‌شده توسط: `CMMS3.RCMEvaluation`، `CMMS3.RCMDecisionLogicNode`
