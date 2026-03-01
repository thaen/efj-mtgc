"""
Generated from intent: binders_create_and_manage
Generated at: 2026-03-01T00:12:41Z
System version: d11cf4c
Intent hash: af906972c09537c8
"""


def steps(harness):
    harness.click_by_text("New Binder")
    harness.fill_by_placeholder("My Trade Binder", "Test Binder")
    harness.fill_by_placeholder("e.g. blue, black ultra pro", "red")
    harness.click_by_text("Save")
    harness.click_by_text("Add Cards")
    harness.fill_by_placeholder("Search by name...", "Condemn")
    harness.click_by_text("Condemn")
    harness.click_by_text("Add Selected")
    harness.screenshot("final_state")
