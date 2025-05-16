# Substrate API

The Substrate API provides endpoints for managing substrate types and batches.

## Base URL

```
/substrate
```

## Endpoints

### Substrate Types

#### Create Substrate Type

```
POST /substrate/types
```

Creates a new substrate type.

#### Request Body

```json
{
  "name": "String",
  "type": "SLUDGE",
  "description": "String",
  "attributes": [
    {
      "name": "String",
      "value": "String",
      "unit": "String"
    }
  ]
}
```

#### Response

Returns the created substrate type.

#### Get All Substrate Types

```
GET /substrate/types
```

Gets all substrate types.

#### Response

```json
[
  {
    "id": "String",
    "name": "String",
    "type": "SLUDGE",
    "description": "String",
    "attributes": [
      {
        "name": "String",
        "value": "String",
        "unit": "String"
      }
    ],
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

#### Get Substrate Type

```
GET /substrate/types/{substrate_type_id}
```

Gets a substrate type by ID.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| substrate_type_id | string | The ID of the substrate type |

#### Response

Returns the substrate type.

### Substrate Batches

#### Create Substrate Batch

```
POST /substrate/batches
```

Creates a new substrate batch.

#### Request Body

```json
{
  "farm_id": "String",
  "name": "String",
  "description": "String",
  "components": [
    {
      "substrate_type_id": "String",
      "ratio": 0.5
    }
  ],
  "total_weight": 100,
  "weight_unit": "kg",
  "batch_number": "String",
  "location": "String",
  "attributes": [
    {
      "name": "String",
      "value": "String",
      "unit": "String"
    }
  ]
}
```

#### Response

Returns the created substrate batch.

#### Get Batches by Farm

```
GET /substrate/batches
```

Gets substrate batches for a farm.

#### Query Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| farm_id | string | The ID of the farm |
| active_only | boolean | Filter for active batches only (default: false) |

#### Response

```json
[
  {
    "id": "String",
    "farm_id": "String",
    "name": "String",
    "description": "String",
    "components": [
      {
        "substrate_type_id": "String",
        "ratio": 0.5
      }
    ],
    "total_weight": 100,
    "weight_unit": "kg",
    "batch_number": "String",
    "location": "String",
    "status": "String",
    "attributes": [
      {
        "name": "String",
        "value": "String",
        "unit": "String"
      }
    ],
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:00:00Z"
  }
]
```

#### Get Substrate Batch

```
GET /substrate/batches/{batch_id}
```

Gets a substrate batch by ID.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| batch_id | string | The ID of the substrate batch |

#### Response

Returns the substrate batch.

#### Update Substrate Batch

```
PATCH /substrate/batches/{batch_id}
```

Updates a substrate batch.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| batch_id | string | The ID of the substrate batch |

#### Request Body

```json
{
  "name": "String",
  "description": "String",
  "status": "String",
  "location": "String",
  "total_weight": 100,
  "attributes": [
    {
      "name": "String",
      "value": "String",
      "unit": "String"
    }
  ],
  "change_reason": "String",
  "changed_by": "String"
}
```

#### Response

Returns `true` if the update was successful.

#### Update Batch Status

```
PATCH /substrate/batches/{batch_id}/status
```

Updates the status of a substrate batch.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| batch_id | string | The ID of the substrate batch |

#### Request Body

```json
{
  "status": "String",
  "change_reason": "String",
  "changed_by": "String"
}
```

#### Response

Returns `true` if the update was successful.

#### Get Batch History

```
GET /substrate/batches/{batch_id}/history
```

Gets the change history for a substrate batch.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| batch_id | string | The ID of the substrate batch |

#### Response

Returns the batch change history.
