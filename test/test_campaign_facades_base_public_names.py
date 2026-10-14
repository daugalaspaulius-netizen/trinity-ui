"""Each split facade keeps resolving every public name it bound before its owners moved out.

A facade whose rules moved into owner modules stays the import path callers, tests and
docs use, so a public name it bound before the split -- one it defined, or one it
imported from the rest of ``efm_go`` -- is part of its surface even when no in-repo
caller reads it today. Standard-library, typing and third-party imports and private
names are not surface. The inventories below are frozen at the split: a name leaves one
only when the facade deliberately stops offering it.

Each name a facade binds again by import is listed with the module that holds it, and
a fresh interpreter checks the facade's binding is that module's own object, so no
reload or eviction elsewhere in the suite can decide the result.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import efm_go
from efm_go.subprocess_utf8 import UTF8_TEXT

#: Facade -> the public project names it bound before its split; each must keep resolving.
_BASE_PUBLIC_NAMES: dict[str, frozenset[str]] = {
    "efm_go.acp.client": frozenset("""
        ACP_BACKENDS_ADVERTISED_MODEL_SELECTION ACP_BACKENDS_HARNESS_OWNED_SESSIONS
        ACP_BACKENDS_HOST_AUTH_CALLBACK ACP_BACKENDS_INLINE_COMPACTION
        ACP_BACKENDS_INTERNAL_SANDBOX ACP_BACKENDS_LOAD_WITHOUT_MODES
        ACP_BACKENDS_MEMBER_DISPATCH ACP_BACKENDS_MEMBER_PANEL ACP_BACKENDS_META_IDENTITY
        ACP_BACKENDS_MODEL_EFFORT_PAIR_IDS ACP_BACKENDS_MODEL_VIA_CONFIG_OPTION
        ACP_BACKENDS_POD_HOME_REMAP ACP_BACKENDS_RESUME_WITHOUT_LOAD
        ACP_BACKENDS_SEED_LOCAL_SETTINGS ACP_BACKENDS_SESSION_MCP_ARRAY ACP_BACKENDS_STEER
        ACP_BACKENDS_STRUCTURED_REFUSAL ACP_BACKEND_CLAUDE ACP_BACKEND_CODEX
        ACP_BACKEND_DEEPSEEK ACP_BACKEND_GOOSE ACP_BACKEND_KAS ACP_BACKEND_KIRO
        ACP_BACKEND_LAUNCH ACP_BACKEND_NODE_ADAPTER_PACKAGES ACP_BACKEND_OPENCODE
        ACP_BACKEND_PI ACP_BACKEND_PROCESS_NAMES ACP_CLIENT_CAPABILITIES AcpAuthRequired
        AcpClient AcpError AcpEvent AcpModelUnavailable AcpPermissionNeeded AcpProcessDied
        AcpPromptBusy AcpPromptStats AcpRegistrationRateLimited AcpSandboxInitFailed
        AcpTimeoutError AcpToolGateUnroutable BoundWorkspaceMismatch CLAUDE_ACP_BIN
        CLAUDE_ACP_NPM_PKG CLAUDE_CODE_BIN CLIENT_NAME CLIENT_VERSION CODEX_ACP_BIN
        CODEX_ACP_NPM_PKG COMPACT_WAIT_TIMEOUT_SECS CREDENTIAL_POINTER_ENV_VARS ChildRecord
        DEEPSEEK_GATE_EXTENSION_SHA256 DEEPSEEK_PERMISSION_MODE DEFAULT_MODEL
        DRAIN_YIELD_AFTER_S DerivedSpecSnapshot DerivedSpecStale EVENT_AGENT_SWITCHED
        EVENT_CLEAR_STATUS EVENT_COMPACTION_STATUS EVENT_COMPLETE EVENT_MCP_OAUTH_REQUEST
        EVENT_MCP_SERVER_INITIALIZED EVENT_MCP_SERVER_INIT_FAILURE EVENT_SUBAGENT_ACTIVITY
        EVENT_SUBAGENT_LIST EVENT_TEXT_CHUNK EVENT_THINKING_CHUNK EVENT_TOOL_CALL
        EVENT_TOOL_CALL_UPDATE EVENT_TOOL_RESULT EVIDENCE_SAMPLING ForkGovernanceUnresolved
        GOOSE_VERIFIED_VERSION_PREFIX HOOK_EVENT_POST_TOOL_USE IDENTITY_STORE_ROOTS
        IDENTITY_STORE_ROOT_ENV_VARS JSONRPC_METHOD_NOT_FOUND JsonRpcMessage JsonRpcRequest
        KIROCREW_SPAWNED_ENV KIROCREW_SPAWNED_VALUE KIRO_CLI_BIN KIRO_CLI_SUBCMD
        KNOWN_SESSION_UPDATES LAUNCHER_EXIT_PREFIXES LivenessOracle MCP_ROSTER_COMPLETE_NOTE
        METHOD_AGENT_SWITCHED METHOD_CANCEL METHOD_CLEAR_STATUS METHOD_COMMANDS_EXECUTE
        METHOD_COMPACTION_STATUS METHOD_INITIALIZE METHOD_KIRO_SESSION_UPDATE
        METHOD_MCP_OAUTH_REQUEST METHOD_MCP_SERVER_INITIALIZED
        METHOD_MCP_SERVER_INIT_FAILURE METHOD_METADATA METHOD_PROMPT
        METHOD_REQUEST_PERMISSION METHOD_SESSION_LOAD METHOD_SESSION_NEW
        METHOD_SESSION_RESUME METHOD_SESSION_UPDATE METHOD_SET_MODE METHOD_SET_MODEL
        METHOD_SUBAGENT_LIST_UPDATE MIRRORS MODEL_CONFIG_ID McpSessionReport
        NODE_ADAPTER_ENTRY_SEGMENTS OPENCODE_BIN OPENCODE_INSTALL_COMMAND
        OPTION_ALLOW_ALWAYS OPTION_ALLOW_ONCE OUTCOME_CANCELLED OUTCOME_SELECTED
        OversizeLineUnrecoverable PI_ACP_BIN PI_ACP_NPM_PKG PI_ACP_VERIFIED_VERSION PI_BIN
        PI_GATE_EXTENSION_SHA256 PI_INSTALL_COMMAND PI_MIN_VERSION PI_NPM_PKG
        PROTOCOL_VERSION PROTOCOL_VERSION_CLAUDE PROTOCOL_VERSION_DEEPSEEK
        PROTOCOL_VERSION_GOOSE PROTOCOL_VERSION_OPENCODE PROTOCOL_VERSION_PI
        PROVIDER_ERROR_AUTH PROVIDER_ERROR_CONNECTION PROVIDER_ERROR_CREDENTIAL_PROPAGATION
        PROVIDER_ERROR_HTTP_5XX PROVIDER_ERROR_MALFORMED_REQUEST
        PROVIDER_ERROR_MODEL_UNAVAILABLE PROVIDER_ERROR_SESSION_EXPIRED
        PROVIDER_ERROR_THROTTLE PROVIDER_ERROR_UNKNOWN PROVIDER_ERROR_USAGE_LIMIT
        PiGateExtensionTampered ProviderErrorClass RLIMIT_PROFILE_SESSION_HOST
        SANDBOX_LAYER_CREW SANDBOX_LAYER_HARNESS SECRET_URI_PREFIX
        STOP_REASON_COMPACTION_FAILED STOP_REASON_END_TURN STUB_SESSION_TOKEN_ENV
        TERMINAL_TOOL_STATUSES UPDATE_AGENT_MESSAGE_CHUNK UPDATE_AGENT_THOUGHT_CHUNK
        UPDATE_CONFIG_OPTION UPDATE_CURRENT_MODE UPDATE_TOOL_CALL UPDATE_USAGE
        VERDICT_WORKING acp_tool_gate advertised_model_ids agent_env_scrub_prefixes
        agent_scratch agent_sdk agent_spec_snapshot agent_version_from_init
        apply_pod_bundle_spawn apply_windows_resource_ceiling
        assert_voice_runtime_outside_agent_workspace atomic_write attach_stub_session_token
        augmented_path await_under_no_progress_bound bind_voice_safe_agent_workspace_async
        browser_session_env browser_socket_env build_permission_event build_prompt_blocks
        bump_resolution_generation catalog_row_would_drop cgroup_scope_argv
        classify_provider_error classify_tool_call codex_acp_not_found_message
        compaction_failure_detail compaction_failure_is_transient config_dir
        consult_offloaded corroborate_launcher_refusal create_subprocess_limited
        deepseek_gate_extension_path delegated_workspace_exposes_sealed_target
        derive_edit_diff describe_search_path effort_config_option_id
        effort_config_option_value ensure_agent_materialized error_is_refusal_terminal
        extract_tool_purpose finish_suspended_spawn fire_tool_hooks format_command_result
        gate_envelope get_global_hook_store get_global_skill_read_observer host_auth
        inject_xdist_auto_cap injection_server_names is_auth_failure_output
        is_credential_propagation_delay is_registration_throttle_output
        is_sandbox_init_failure_output is_sensitive_path kiro_cli_not_found_message
        kiro_sessions_dir known_kiro_cli_dirs launch_for launcher_refusal
        log_unrenderable_content logger make_unified_diff meta_builtin_server_names
        mint_stub_session_token mirror_for mise_data_dir model_is_unusable
        model_refusal_phrase model_registry model_registry_namespace model_scope
        note_tool_call_started overlay_project_scope parse_claude_compaction_notice
        parse_codex_compaction_update parse_prompt_token_usage parse_refusal
        parse_session_modes parse_slash_command parse_usage_cost parse_usage_update
        permission_floor pi_gate_extension_path pick_served_default pinned_fs
        platform_compat pooled_session_servers prompt_timeout_for_ceiling record_frame
        record_tool_call_finished redact_credentials redact_exfiltration_urls
        redact_log_via_context redact_text registration_rate_limited_error
        registration_throttle_line release_bound_agent_workspace require_fork_governance
        require_fresh_derived_spec require_unchanged_derived_spec
        resolve_bound_session_workspace resolve_kiro_cli resolve_krb5_ccname
        resolve_pin_spelling resolve_prompt_timeout resolve_secret_uris resolve_usable_model
        response_write_window_secs sandbox_init_failure sandbox_init_failure_for_runtime
        sandbox_init_remediation schedule_claim schedule_session_token_publish
        scrub_agent_subprocess_env seed_provenance sel sel_module session_mcp_deny_rules
        subprocess_executor tool_call_content_text tool_output_fingerprints
        warn_unresolved_server_refs wrap_argv wrap_argv_async wrapped_by_crew_sandbox
        write_notification_best_effort write_response_frame_bounded
        """.split()),
    "efm_go.cron": frozenset("""
        CHANNEL_MAX_LEN CRON_FIRES CronFolderLookup CronHistoryStore CronJob
        CronLoopSafetyError CronPendingMismatch CronRunRecord CronSchedule CronService
        CronStoreBusy CronStoreUnreadable KiroCrewConfig MAX_CRON_MESSAGE MAX_SHORT_STRING
        ProcessHandle add_handle admission_check agent_sequence_dispatches
        authorize_runtime_kill bind_cron_memory build_cron_session_context
        compute_next_run_ts config_dir cron_expr_matches cron_gate_budget cron_inflight
        cron_job_id_from_session_key cron_owner_matches cron_script
        cron_session_key_is_stable cron_store_lock data_home dispatched_agents_from_disk
        effective_wake_budget emit_counter enabled_count_from_disk ending_fence
        env_flag_enabled failure_name format_schedule get_local_tz is_valid_skip_date
        is_valid_timezone job_agent_names_from_disk job_pause_state_from_disk join_failures
        kill_each kill_set kill_verified_process load_cron_folders logger
        lookup_cron_folder_id parse_time_string platform_compat process_handle_of
        process_survived_async published_config_timezone referenced_skill_names
        release_teardown_lease resolve_cron_memory sel shutdown_event spawn_in_flight
        stall_attribution subprocess_executor teardown_barriers teardown_capture
        unhealthy_jobs_from_disk validate_cron_expr with_kill_failure
        """.split()),
    "efm_go.autonudge": frozenset("""
        ADDRESSING_FIELDS APPROVAL_STALL_REASON AUTONUDGE_STOP_REASON AutoNudgeService
        AutoNudgeStaleBaseline AutoNudgeStoreUnvetted MANUAL_STOP_REASON MAX_BANNER_CHARS
        MONITOR_BUSY_RETRY_SECS MONITOR_COMPLETION_EVIDENCE_TIMEOUT_SECS
        MONITOR_STATE_VERSION MONITOR_STOP_APPROVAL_STALL
        MONITOR_STOP_COMPLETION_UNAVAILABLE MONITOR_STOP_SESSION_CLOSE
        MONITOR_STOP_SESSION_UNAVAILABLE MONITOR_STOP_UNSUPPORTED_VERSION MONITOR_STOP_USER
        MONITOR_TERMINAL_REASON MonitorActionCompletion MonitorActionDisposition
        MonitorBudgets MonitorCreationSurface MonitorDecision MonitorDispatchResult
        MonitorObservationStatus MonitorOutcome MonitorProbeResult MonitorState
        MonitorUpdateConflict MonitorVerdict NUDGE_RENEW_DUE_SHARE NudgeAdmissionRefused
        NudgeLoop PlatformCompositionError REVIEW_READY SENTINEL_DROPPED_REASON
        SESSION_START_FAILURE_REASON STRUCTURAL_TERMINAL_REASON autonudge_stop_log
        binding_key_for config_dir data_home decide_monitor enabled fsync_dir get_instance
        infer_monitor infer_subject irq is_channel_key is_sensitive_path
        is_structured_monitor_loop is_unattempted_probe kind_supports_objective legacy_home
        logger loop_subject monitor_budget_reason monitor_stall_reason
        monitor_state_from_dict monitor_state_to_dict new_goal_token nudge_cycle_header
        platform_compat probes quarantine_monitor_state redact_credentials
        redact_exfiltration_urls redact_log_via_context redact_store_value
        redact_via_context repair_sentinel_path replace_with_retry
        retained_outcome_blocks_rearm runtime_budget_exceeded scrub_loop_text
        scrubbed_judge_spec shutdown_event stamp_monitor_alerted
        structured_monitor_binding_key_for targets terminal_notification_delivery_matches
        validate_runtime_secs validation
        """.split()),
    "efm_go.apps.builtins.ops_mission_control.backend.routes": frozenset("""
        APP_NAME CLAIMED_BY_OPERATOR CronStoreUnreadable DEFAULT_VERIFY_AFTER_SECS
        EXPIRING_ACTIONS Handler LedgerEntry MAX_INCIDENTS_RESPONSE MODE_ORDER STATE_FIRING
        STATE_OK STATE_SUPPRESSED STATUS_NEEDS_HUMAN Signal UnknownFieldError VALID_ACTIONS
        VERIFIABLE_ACTIONS VERIFY_NOT_CHECKABLE VERIFY_PENDING canonical_slot_key companion
        delete_secret describe_secrets dispatch get_registry handover is_app_enabled ledger
        logger merge_provider_config notify_out policy_store provider_config put_secret
        redact_tokens redact_via_context register_routes resolve_silence_secs rotation sel
        set_top_level slack_out slot_watch store utc_now_iso webhook_mod
        """.split()),
    "efm_go.apps.builtins.issue_radar.backend.routes": frozenset("""
        GhCliError GhInvalidInputError GhPermissionError GhSetupError KiroCrewConfig
        LIST_POLL_MAX_STALENESS_SEC LoopBoundLock MAX_ASSIGNEES MAX_ITEM_NUMBER MAX_RUN_ID
        PrSearchError github_client is_app_enabled logger normalize_ui_language_tag
        pipeline_routes provider register_routes sel store ui_language_tag watch
        """.split()),
    "efm_go.mcp_gateway.gatewayd": frozenset("""
        Admission Backend BackendGone BackendPool BackendUnavailable CANONICAL_TEMP_KEYS
        CONTROL_PLANE_BACKENDS CallerContext CircuitBreaker DEFAULT_CAPACITY DEFAULT_CEILING
        DEFAULT_FLOOR DRAIN_DEADLINE_SECS DRAIN_SECS HostBudget HostBudgetExhausted
        HostBudgetLimits HostCharge HotKeyStore INTERNAL_STUB_PREFIXES IS_WINDOWS
        KIROCREW_BIN_MCP_SERVERS KiroCrewConfig OUTCOME_FAILURE OUTCOME_NEUTRAL OnQueued
        POOL_SHUTDOWN_SECS Permit PoolAtCapacity PoolKey READ_BUFFER_LIMIT_BYTES
        REGISTERED_CAPABILITIES REJECT_CLASS_CAPACITY REJECT_CLASS_COMPAT
        REJECT_CLASS_ISOLATION SECRET_URI_PREFIX STUB_KEEPALIVE_TYPE SecurityEventLog
        SpawnGate SpawnGateClosed SpawnGateTimeout TargetResolver apps_sweep_spool
        classify_declared_temp_env cleanup_old_spill_files code_fingerprint
        configure_default_executor credwatch declared_temp_refusal_reasons
        default_hot_keys_path env_sidecar_dir env_sidecar_name env_target_resolver
        format_declared_temp_refusals forward_declared_env_enabled get_recorder hash_command
        hash_effective_env hazards is_credential_env_key efm_go launch_approval logger
        main maintenance_executor mcp_search_path new_tenant_nonce non_secret_env
        pool_identity_env_keys prewarm_from_payloads records_dir redact
        resolvable_target_stems resolve_limits resolve_once_resolver resolve_overlay_dir
        resolve_peer_identity resolve_secret_uris resolved_launch run_gatewayd socketsec
        spawn_backend spec_path_key stub_fallback_counts subprocess_executor
        sweep_all_backend_tmp tool_surface transport warm_backend warm_code_fingerprint
        """.split()),
}

#: Facade -> ``{name: module holding it}`` for each base name the facade re-binds by import.
_REBOUND: dict[str, dict[str, str]] = {
    "efm_go.acp.client": {
        "ACP_BACKENDS_HOST_AUTH_CALLBACK": "efm_go.acp.types",
        "LAUNCHER_EXIT_PREFIXES": "efm_go.sandbox",
        "SANDBOX_LAYER_CREW": "efm_go.sandbox",
        "SANDBOX_LAYER_HARNESS": "efm_go.sandbox",
        "launcher_refusal": "efm_go.sandbox",
        "sandbox_init_remediation": "efm_go.sandbox",
    },
    "efm_go.cron": {
        "CHANNEL_MAX_LEN": "efm_go.validation",
        "MAX_CRON_MESSAGE": "efm_go.validation",
        "MAX_SHORT_STRING": "efm_go.validation",
        "cron_gate_budget": "efm_go.executors",
        "platform_compat": "efm_go",
    },
    "efm_go.autonudge": {
        "MONITOR_BUSY_RETRY_SECS": "efm_go.monitoring.models",
        "MONITOR_COMPLETION_EVIDENCE_TIMEOUT_SECS": "efm_go.monitoring.models",
        "MONITOR_STOP_APPROVAL_STALL": "efm_go.monitoring.models",
        "MONITOR_STOP_SESSION_CLOSE": "efm_go.monitoring.models",
        "MONITOR_STOP_USER": "efm_go.monitoring.models",
        "MonitorActionCompletion": "efm_go.monitoring.models",
        "MonitorActionDisposition": "efm_go.monitoring.models",
        "MonitorBudgets": "efm_go.monitoring.models",
        "MonitorCreationSurface": "efm_go.monitoring.models",
        "MonitorDecision": "efm_go.monitoring.models",
        "MonitorObservationStatus": "efm_go.monitoring.models",
        "MonitorProbeResult": "efm_go.monitoring.models",
        "MonitorVerdict": "efm_go.monitoring.models",
        "REVIEW_READY": "efm_go.monitoring.registry",
        "data_home": "efm_go.config.loader",
        "decide_monitor": "efm_go.monitoring.decision",
        "is_unattempted_probe": "efm_go.monitoring.github_provider_errors",
        "kind_supports_objective": "efm_go.monitoring.registry",
        "monitor_budget_reason": "efm_go.monitoring.decision",
        "monitor_stall_reason": "efm_go.monitoring.decision",
        "monitor_state_to_dict": "efm_go.monitoring.models",
        "platform_compat": "efm_go",
        "probes": "efm_go",
        "retained_outcome_blocks_rearm": "efm_go.monitoring.models",
        "shutdown_event": "efm_go",
        "stamp_monitor_alerted": "efm_go.monitoring.decision",
        "targets": "efm_go.probes",
        "validate_runtime_secs": "efm_go.monitoring.limits",
    },
    "efm_go.apps.builtins.ops_mission_control.backend.routes": {
        "CLAIMED_BY_OPERATOR": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "CronStoreUnreadable": "efm_go.cron",
        "DEFAULT_VERIFY_AFTER_SECS": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "EXPIRING_ACTIONS": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "LedgerEntry": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "MODE_ORDER": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "STATE_FIRING": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "STATE_OK": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "STATE_SUPPRESSED": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "STATUS_NEEDS_HUMAN": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "Signal": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "UnknownFieldError": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "VALID_ACTIONS": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "VERIFIABLE_ACTIONS": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "VERIFY_NOT_CHECKABLE": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "VERIFY_PENDING": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "describe_secrets": "efm_go.apps.builtins.ops_mission_control.backend.secrets",
        "provider_config": "efm_go.apps.builtins.ops_mission_control.backend.providers",
        "resolve_silence_secs": "efm_go.apps.builtins.ops_mission_control.backend.models",
        "set_top_level": "efm_go.apps.builtins.ops_mission_control.backend.providers",
        "utc_now_iso": "efm_go.apps.builtins.ops_mission_control.backend.models",
    },
    "efm_go.apps.builtins.issue_radar.backend.routes": {
        "KiroCrewConfig": "efm_go.config.loader",
        "normalize_ui_language_tag": "efm_go.context",
        "ui_language_tag": "efm_go.context",
    },
    "efm_go.mcp_gateway.gatewayd": {
        "BackendGone": "efm_go.mcp_gateway.backend",
        "BackendUnavailable": "efm_go.mcp_gateway.pool",
        "CallerContext": "efm_go.mcp_caller",
        "DRAIN_DEADLINE_SECS": "efm_go.mcp_gateway.pool",
        "HostBudgetExhausted": "efm_go.mcp_gateway.host_budget",
        "KIROCREW_BIN_MCP_SERVERS": "efm_go.mcp_cleanup",
        "PoolAtCapacity": "efm_go.mcp_gateway.pool",
        "SpawnGateClosed": "efm_go.mcp_gateway.admission",
        "SpawnGateTimeout": "efm_go.mcp_gateway.admission",
        "code_fingerprint": "efm_go.code_fingerprint",
        "configure_default_executor": "efm_go.executors",
        "env_sidecar_dir": "efm_go.mcp_gateway.rewriter",
        "env_sidecar_name": "efm_go.mcp_gateway.rewriter",
        "hash_command": "efm_go.mcp_gateway.hashing",
        "hash_effective_env": "efm_go.mcp_gateway.hashing",
        "is_credential_env_key": "efm_go.mcp_gateway.manager",
        "new_tenant_nonce": "efm_go.mcp_caller",
        "non_secret_env": "efm_go.mcp_gateway.hashing",
        "prewarm_from_payloads": "efm_go.mcp_gateway.prewarm",
        "resolve_overlay_dir": "efm_go.mcp_gateway.rewriter",
        "resolve_peer_identity": "efm_go.peer_resolve",
        "subprocess_executor": "efm_go.executors",
        "tool_surface": "efm_go.mcp_gateway",
    },
}

_PROBE = """
import importlib, json, sys
rebound = json.loads(sys.argv[1])
checked, wrong = 0, []
for facade, names in rebound.items():
    module = importlib.import_module(facade)
    for name, home in names.items():
        checked += 1
        if getattr(module, name, None) is not getattr(importlib.import_module(home), name):
            wrong.append(f"{facade}.{name}")
print(json.dumps({"checked": checked, "wrong": wrong}))
"""


@pytest.mark.parametrize("facade", sorted(_BASE_PUBLIC_NAMES))
def test_every_base_public_name_resolves_on_its_facade(facade: str) -> None:
    module = importlib.import_module(facade)
    assert sorted(name for name in _BASE_PUBLIC_NAMES[facade] if not hasattr(module, name)) == []


def test_every_rebound_name_is_a_base_public_name_of_its_facade() -> None:
    assert set(_REBOUND) == set(_BASE_PUBLIC_NAMES)
    for facade, names in _REBOUND.items():
        assert names and set(names) <= _BASE_PUBLIC_NAMES[facade], facade


def test_a_rebound_name_is_the_object_its_home_module_holds(tmp_path: Path) -> None:
    """Checked in a fresh interpreter, so no module another test reloaded or evicted
    can make a copy look like the original, or the original look like a copy. The child
    runs in ``tmp_path``, so anything an import writes by a relative path stays there."""
    env = dict(os.environ)
    src = str(Path(efm_go.__file__).resolve().parents[1])
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    out = subprocess.run(
        [sys.executable, "-c", _PROBE, json.dumps(_REBOUND)],
        capture_output=True,
        check=True,
        env=env,
        cwd=tmp_path,
        timeout=60,
        **UTF8_TEXT,
    )
    result = json.loads(out.stdout.splitlines()[-1])
    assert result == {"checked": sum(map(len, _REBOUND.values())), "wrong": []}, out.stderr
