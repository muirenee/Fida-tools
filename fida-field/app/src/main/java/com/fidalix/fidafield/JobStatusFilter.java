package com.fidalix.fidafield;

/** Shared meaning for the dashboard count and its destination list. */
final class JobStatusFilter {
    static final String ACTIVE = "Active jobs";
    static final String ACTIVE_SQL = "status IN ('Open','In Progress')";

    private JobStatusFilter() {}

    static String activeSql(String alias) {
        return alias + "." + ACTIVE_SQL;
    }
}
