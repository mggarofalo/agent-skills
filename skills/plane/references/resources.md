# Plane CLI Resource Reference

Auto-generated on 2026-08-08.

## Project

### `plane project create`

MCP tool: `project_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--identifier` | string | yes | |
| `--name` | string | yes | |
| `--archive-in` | number | no | |
| `--close-in` | number | no | |
| `--cover-image` | string | no | |
| `--cycle-view` | boolean | no | |
| `--default-assignee` | string | no | |
| `--description` | string | no | |
| `--emoji` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--guest-view-all-features` | boolean | no | |
| `--icon-prop` | string | no | |
| `--intake-view` | boolean | no | |
| `--is-issue-type-enabled` | boolean | no | |
| `--is-time-tracking-enabled` | boolean | no | |
| `--issue-views-view` | boolean | no | |
| `--module-view` | boolean | no | |
| `--page-view` | boolean | no | |
| `--project-lead` | string | no | |
| `--timezone` | string | no | |

### `plane project list`

MCP tool: `project_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane project get`

MCP tool: `project_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane project update`

MCP tool: `project_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--archive-in` | number | no | |
| `--close-in` | number | no | |
| `--cover-image` | string | no | |
| `--cycle-view` | boolean | no | |
| `--default-assignee` | string | no | |
| `--default-state` | string | no | |
| `--description` | string | no | |
| `--emoji` | string | no | |
| `--estimate` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--guest-view-all-features` | boolean | no | |
| `--icon-prop` | string | no | |
| `--identifier` | string | no | |
| `--intake-view` | boolean | no | |
| `--is-issue-type-enabled` | boolean | no | |
| `--is-time-tracking-enabled` | boolean | no | |
| `--issue-views-view` | boolean | no | |
| `--module-view` | boolean | no | |
| `--name` | string | no | |
| `--page-view` | boolean | no | |
| `--project-lead` | string | no | |
| `--timezone` | string | no | |

### `plane project delete`

MCP tool: `project_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane project ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## State

### `plane state create`

MCP tool: `state_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--color` | string | yes | |
| `--name` | string | yes | |
| `--default` | boolean | no | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--group` | string | no | |
| `--is-triage` | boolean | no | |
| `--sequence` | number | no | |

### `plane state list`

MCP tool: `state_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane state get`

MCP tool: `state_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/{state_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--state-id` | string | yes | accepts name or UUID |

### `plane state update`

MCP tool: `state_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/{state_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--state-id` | string | yes | accepts name or UUID |
| `--color` | string | no | |
| `--default` | boolean | no | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--group` | string | no | |
| `--is-triage` | boolean | no | |
| `--name` | string | no | |
| `--sequence` | number | no | |

### `plane state delete`

MCP tool: `state_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/states/{state_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--state-id` | string | yes | accepts name or UUID |


### `plane state ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Label

### `plane label create`

MCP tool: `label_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--color` | string | no | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--sort-order` | number | no | |

### `plane label list`

MCP tool: `label_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane label get`

MCP tool: `label_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/{label_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--label-id` | string | yes | accepts name or UUID |

### `plane label update`

MCP tool: `label_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/{label_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--label-id` | string | yes | accepts name or UUID |
| `--color` | string | no | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--name` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--sort-order` | number | no | |

### `plane label delete`

MCP tool: `label_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/labels/{label_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--label-id` | string | yes | accepts name or UUID |


### `plane label ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Issue

### `plane issue create`

MCP tool: `issue_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--archived-at` | string | no | |
| `--assignees` | string[] | no | |
| `--completed-at` | string | no | |
| `--created-by` | string | no | |
| `--deleted-at` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--estimate-point` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--is-draft` | boolean | no | |
| `--labels` | string[] | no | |
| `--last-activity-at` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--point` | number | no | |
| `--priority` | string | no | |
| `--sequence-id` | number | no | |
| `--sort-order` | number | no | |
| `--start-date` | string | no | |
| `--state` | string | no | accepts name or UUID |
| `--target-date` | string | no | |
| `--type` | string | no | |
| `--type-id` | string | no | |

### `plane issue list`

MCP tool: `issue_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane issue get`

MCP tool: `issue_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--expand` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |

### `plane issue get-by-sequence-id`

MCP tool: `issue_get_by_sequence_id`

**GET** `/api/v1/workspaces/{workspace_slug}/work-items/{project_identifier}-{issue_identifier}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--issue-identifier` | string | yes | |
| `--project-identifier` | string | yes | |

### `plane issue search`

MCP tool: `issue_search`

**GET** `/api/v1/workspaces/{workspace_slug}/work-items/search/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--search` | string | yes | |
| `--limit` | number | no | |
| `--workspace-search` | string | no | |

### `plane issue update`

MCP tool: `issue_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--archived-at` | string | no | |
| `--assignees` | string[] | no | |
| `--completed-at` | string | no | |
| `--created-by` | string | no | |
| `--deleted-at` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--estimate-point` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--is-draft` | boolean | no | |
| `--labels` | string[] | no | |
| `--last-activity-at` | string | no | |
| `--name` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--point` | number | no | |
| `--priority` | string | no | |
| `--sequence-id` | number | no | |
| `--sort-order` | number | no | |
| `--start-date` | string | no | |
| `--state` | string | no | accepts name or UUID |
| `--target-date` | string | no | |
| `--type` | string | no | |
| `--type-id` | string | no | |

### `plane issue delete`

MCP tool: `issue_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane issue ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Link

### `plane link add`

MCP tool: `link_add`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--url` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--title` | string | no | |

### `plane link list`

MCP tool: `link_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane link get`

MCP tool: `link_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane link update`

MCP tool: `link_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--title` | string | no | |
| `--url` | string | no | |

### `plane link delete`

MCP tool: `link_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |


## Activity

### `plane activity list`

MCP tool: `activity_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/activities/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane activity get`

MCP tool: `activity_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/activities/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |


## Comment

### `plane comment add`

MCP tool: `comment_add`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--access` | string | no | |
| `--comment` | string | no | |
| `--comment-json` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane comment list`

MCP tool: `comment_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane comment get`

MCP tool: `comment_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane comment update`

MCP tool: `comment_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--access` | string | no | |
| `--comment` | string | no | |
| `--comment-json` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--parent` | string | no | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane comment delete`

MCP tool: `comment_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |


## Attachment

### `plane attachment list`

MCP tool: `attachment_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane attachment get`

MCP tool: `attachment_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane attachment get-upload-credentials`

MCP tool: `attachment_get_upload_credentials`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--size` | number | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--type` | string | no | |

### `plane attachment upload-file`

MCP tool: `attachment_upload_file`

**GET** ``

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--file` | string | yes | |
| `--key` | string | yes | |
| `--policy` | string | yes | |

### `plane attachment complete-upload`

MCP tool: `attachment_complete_upload`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--is-uploaded` | boolean | no | |

### `plane attachment update`

MCP tool: `attachment_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--is-uploaded` | boolean | no | |

### `plane attachment delete`

MCP tool: `attachment_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/attachments/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |


## Cycle

### `plane cycle create`

MCP tool: `cycle_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--description` | string | no | |
| `--end-date` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--owned-by` | string | no | |
| `--start-date` | string | no | |
| `--timezone` | string | no | |

### `plane cycle add-work-items`

MCP tool: `cycle_add_work_items`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |
| `--issues` | string[] | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane cycle transfer-work-items`

MCP tool: `cycle_transfer_work_items`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/transfer-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |
| `--new-cycle-id` | string | yes | |

### `plane cycle archive`

MCP tool: `cycle_archive`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/archive/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |

### `plane cycle list`

MCP tool: `cycle_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--cycle-view` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane cycle get`

MCP tool: `cycle_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane cycle list-work-items`

MCP tool: `cycle_list_work_items`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |
| `--cursor` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane cycle list-archived`

MCP tool: `cycle_list_archived`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/archived-cycles/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane cycle update`

MCP tool: `cycle_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--description` | string | no | |
| `--end-date` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--name` | string | no | |
| `--owned-by` | string | no | |
| `--start-date` | string | no | |
| `--timezone` | string | no | |

### `plane cycle unarchive`

MCP tool: `cycle_unarchive`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/archived-cycles/{cycle_id}/unarchive/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |

### `plane cycle remove-work-item`

MCP tool: `cycle_remove_work_item`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{cycle_id}/cycle-issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cycle-id` | string | yes | accepts name or UUID |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane cycle delete`

MCP tool: `cycle_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/cycles/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane cycle ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Module

### `plane module create`

MCP tool: `module_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--lead` | string | no | |
| `--members` | string[] | no | |
| `--start-date` | string | no | |
| `--status` | string | no | |
| `--target-date` | string | no | |

### `plane module add-work-items`

MCP tool: `module_add_work_items`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--issues` | string[] | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--module-id` | string | yes | accepts name or UUID |

### `plane module archive`

MCP tool: `module_archive`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{resource_id}/archive/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane module list`

MCP tool: `module_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane module get`

MCP tool: `module_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane module list-work-items`

MCP tool: `module_list_work_items`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--module-id` | string | yes | accepts name or UUID |
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane module list-archived`

MCP tool: `module_list_archived`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/archived-modules/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--order-by` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane module update`

MCP tool: `module_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--description` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--lead` | string | no | |
| `--members` | string[] | no | |
| `--name` | string | no | |
| `--start-date` | string | no | |
| `--status` | string | no | |
| `--target-date` | string | no | |

### `plane module unarchive`

MCP tool: `module_unarchive`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/archived-modules/{resource_id}/unarchive/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane module remove-work-item`

MCP tool: `module_remove_work_item`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{module_id}/module-issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--module-id` | string | yes | accepts name or UUID |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane module delete`

MCP tool: `module_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/modules/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane module ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Page

### `plane page add-workspace`

MCP tool: `page_add_workspace`

**POST** `/api/v1/workspaces/{workspace_slug}/pages/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--description` | string | yes | |
| `--name` | string | yes | |
| `--access` | string | no | |
| `--archived-at` | string | no | |
| `--color` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--is-locked` | boolean | no | |
| `--logo-props` | string | no | |
| `--view-props` | string | no | |

### `plane page add-project`

MCP tool: `page_add_project`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--description` | string | yes | |
| `--name` | string | yes | |
| `--access` | string | no | |
| `--archived-at` | string | no | |
| `--color` | string | no | |
| `--external-id` | string | no | |
| `--external-source` | string | no | |
| `--is-locked` | boolean | no | |
| `--logo-props` | string | no | |
| `--view-props` | string | no | |

### `plane page get-workspace`

MCP tool: `page_get_workspace`

**GET** `/api/v1/workspaces/{workspace_slug}/pages/{page_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--page-id` | string | yes | |

### `plane page get-project`

MCP tool: `page_get_project`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/{page_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--page-id` | string | yes | |


## Intake

### `plane intake add`

MCP tool: `intake_add`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--issue` | string | yes | |

### `plane intake list`

MCP tool: `intake_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--expand` | string | no | |
| `--fields` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane intake get`

MCP tool: `intake_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane intake update`

MCP tool: `intake_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--duplicate-to` | string | no | |
| `--issue` | string | no | |
| `--snoozed-till` | string | no | |
| `--source` | string | no | |
| `--source-email` | string | no | |
| `--status` | string | no | |

### `plane intake delete`

MCP tool: `intake_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/intake-issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |


### `plane intake ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Worklog

### `plane worklog create`

MCP tool: `worklog_create`

**POST** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/worklogs/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--duration` | number | no | |
| `--updated-by` | string | no | |

### `plane worklog get-for-issue`

MCP tool: `worklog_get_for_issue`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/worklogs/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane worklog get-total-time`

MCP tool: `worklog_get_total_time`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/total-worklogs/`

### `plane worklog update`

MCP tool: `worklog_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/worklogs/{worklog_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--worklog-id` | string | yes | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--duration` | number | no | |
| `--updated-by` | string | no | |

### `plane worklog delete`

MCP tool: `worklog_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/worklogs/{worklog_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |
| `--worklog-id` | string | yes | |


## Epic

### `plane epic list`

MCP tool: `epic_list`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/epics/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane epic get`

MCP tool: `epic_get`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/epics/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--fields` | string | no | |


## Initiative

### `plane initiative create`

MCP tool: `initiative_create`

**POST** `/api/v1/workspaces/{workspace_slug}/initiatives/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--archived-at` | string | no | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--end-date` | string | no | |
| `--lead` | string | no | |
| `--logo-props` | string | no | |
| `--start-date` | string | no | |
| `--state` | string | no | accepts name or UUID |
| `--updated-by` | string | no | |

### `plane initiative list`

MCP tool: `initiative_list`

**GET** `/api/v1/workspaces/{workspace_slug}/initiatives/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane initiative get`

MCP tool: `initiative_get`

**GET** `/api/v1/workspaces/{workspace_slug}/initiatives/{initiative_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--initiative-id` | string | yes | |

### `plane initiative update`

MCP tool: `initiative_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/initiatives/{initiative_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--initiative-id` | string | yes | |
| `--archived-at` | string | no | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--end-date` | string | no | |
| `--lead` | string | no | |
| `--logo-props` | string | no | |
| `--name` | string | no | |
| `--start-date` | string | no | |
| `--state` | string | no | accepts name or UUID |
| `--updated-by` | string | no | |

### `plane initiative delete`

MCP tool: `initiative_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/initiatives/{initiative_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--initiative-id` | string | yes | |


### `plane initiative ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Customer

### `plane customer add`

MCP tool: `customer_add`

**POST** `/api/v1/workspaces/{workspace_slug}/customers/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--archived-at` | string | no | |
| `--contract-status` | string | no | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--domain` | string | no | |
| `--email` | string | no | |
| `--employees` | number | no | |
| `--logo-asset` | string | no | |
| `--logo-props` | string | no | |
| `--revenue` | string | no | |
| `--stage` | string | no | |
| `--updated-by` | string | no | |
| `--website-url` | string | no | |

### `plane customer link-work-items`

MCP tool: `customer_link_work_items`

**POST** `/api/v1/workspaces/{workspace_slug}/customers/{customer_id}/issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--customer-id` | string | yes | |
| `--issue-ids` | string[] | yes | |

### `plane customer list`

MCP tool: `customer_list`

**GET** `/api/v1/workspaces/{workspace_slug}/customers/`

### `plane customer get`

MCP tool: `customer_get`

**GET** `/api/v1/workspaces/{workspace_slug}/customers/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane customer list-work-items`

MCP tool: `customer_list_work_items`

**GET** `/api/v1/workspaces/{workspace_slug}/customers/{customer_id}/issues/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--customer-id` | string | yes | |

### `plane customer update`

MCP tool: `customer_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/customers/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--archived-at` | string | no | |
| `--contract-status` | string | no | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--domain` | string | no | |
| `--email` | string | no | |
| `--employees` | number | no | |
| `--logo-asset` | string | no | |
| `--logo-props` | string | no | |
| `--name` | string | no | |
| `--revenue` | string | no | |
| `--stage` | string | no | |
| `--updated-by` | string | no | |
| `--website-url` | string | no | |

### `plane customer unlink-work-item`

MCP tool: `customer_unlink_work_item`

**DELETE** `/api/v1/workspaces/{workspace_slug}/customers/{customer_id}/issues/{work_item_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--customer-id` | string | yes | |
| `--work-item-id` | string | yes | accepts UUID or sequence ID (e.g. PROJ-42) |

### `plane customer delete`

MCP tool: `customer_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/customers/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane customer ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Teamspace

### `plane teamspace create`

MCP tool: `teamspace_create`

**POST** `/api/v1/workspaces/{workspace_slug}/teamspaces/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--name` | string | yes | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-json` | string | no | |
| `--description-stripped` | string | no | |
| `--lead` | string | no | |
| `--logo-props` | string | no | |
| `--updated-by` | string | no | |

### `plane teamspace list`

MCP tool: `teamspace_list`

**GET** `/api/v1/workspaces/{workspace_slug}/teamspaces/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--cursor` | string | no | |
| `--per-page` | number | no | enum: 20, max |

### `plane teamspace get`

MCP tool: `teamspace_get`

**GET** `/api/v1/workspaces/{workspace_slug}/teamspaces/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane teamspace update`

MCP tool: `teamspace_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/teamspaces/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--created-by` | string | no | |
| `--description` | string | no | |
| `--description-json` | string | no | |
| `--description-stripped` | string | no | |
| `--lead` | string | no | |
| `--logo-props` | string | no | |
| `--name` | string | no | |
| `--updated-by` | string | no | |

### `plane teamspace delete`

MCP tool: `teamspace_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/teamspaces/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane teamspace ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Sticky

### `plane sticky add`

MCP tool: `sticky_add`

**POST** `/api/v1/workspaces/{workspace_slug}/stickies/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--background-color` | string | no | |
| `--color` | string | no | |
| `--created-by` | string | no | |
| `--deleted-at` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--logo-props` | string | no | |
| `--name` | string | no | |
| `--sort-order` | number | no | |
| `--updated-by` | string | no | |

### `plane sticky list`

MCP tool: `sticky_list`

**GET** `/api/v1/workspaces/{workspace_slug}/stickies/`

### `plane sticky get`

MCP tool: `sticky_get`

**GET** `/api/v1/workspaces/{workspace_slug}/stickies/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |

### `plane sticky update`

MCP tool: `sticky_update`

**PATCH** `/api/v1/workspaces/{workspace_slug}/stickies/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |
| `--background-color` | string | no | |
| `--color` | string | no | |
| `--created-by` | string | no | |
| `--deleted-at` | string | no | |
| `--description` | string | no | |
| `--description-stripped` | string | no | |
| `--logo-props` | string | no | |
| `--name` | string | no | |
| `--sort-order` | number | no | |
| `--updated-by` | string | no | |

### `plane sticky delete`

MCP tool: `sticky_delete`

**DELETE** `/api/v1/workspaces/{workspace_slug}/stickies/{resource_id}/`

| Flag | Type | Required | Notes |
|------|------|----------|-------|
| `--resource-id` | string | yes | |


### `plane sticky ensure`

Idempotent create-or-update by name. Accepts the same flags as create/update.

## Member

### `plane member get-workspace`

MCP tool: `member_get_workspace`

**GET** `/api/v1/workspaces/{workspace_slug}/members/`

### `plane member get-project`

MCP tool: `member_get_project`

**GET** `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/project-members/`


