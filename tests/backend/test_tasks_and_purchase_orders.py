"""
Tests for task and purchase order API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_in_memory_state():
    """Restore the module-level task and purchase order lists after each test."""
    tasks_snapshot = list(main.tasks)
    purchase_orders_snapshot = list(main.purchase_orders)
    yield
    main.tasks[:] = tasks_snapshot
    main.purchase_orders[:] = purchase_orders_snapshot


@pytest.fixture
def new_task():
    """Valid task creation payload."""
    return {"title": "Check stock levels", "priority": "high", "dueDate": "2026-11-01"}


@pytest.fixture
def new_purchase_order():
    """Valid purchase order creation payload for backlog item 1."""
    return {
        "backlog_item_id": "1",
        "supplier_name": "Acme Components",
        "quantity": 350,
        "unit_cost": 4.5,
        "expected_delivery_date": "2026-11-15",
        "notes": "Expedite if possible",
    }


class TestTaskEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks(self, client, new_task):
        """Test getting all tasks returns created tasks, newest first."""
        first = client.post("/api/tasks", json=new_task).json()
        second = client.post("/api/tasks", json={**new_task, "title": "Second"}).json()

        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert [t["id"] for t in data[:2]] == [second["id"], first["id"]]

    def test_create_task(self, client, new_task):
        """Test creating a task returns it as pending with all fields."""
        response = client.post("/api/tasks", json=new_task)
        assert response.status_code == 200

        task = response.json()
        assert isinstance(task["id"], str)
        assert task["title"] == new_task["title"]
        assert task["priority"] == "high"
        assert task["dueDate"] == "2026-11-01"
        assert task["status"] == "pending"

    def test_create_task_default_priority(self, client, new_task):
        """Test that priority defaults to medium when omitted."""
        payload = {k: v for k, v in new_task.items() if k != "priority"}
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 200
        assert response.json()["priority"] == "medium"

    def test_create_task_strips_title(self, client, new_task):
        """Test that surrounding whitespace is removed from the title."""
        response = client.post("/api/tasks", json={**new_task, "title": "  Padded  "})
        assert response.json()["title"] == "Padded"

    @pytest.mark.parametrize("override", [
        {"title": ""},
        {"title": "x" * 201},
        {"priority": "urgent"},
        {"dueDate": "not-a-date"},
    ])
    def test_create_task_invalid_input(self, client, new_task, override):
        """Test that invalid task payloads are rejected with 422."""
        response = client.post("/api/tasks", json={**new_task, **override})
        assert response.status_code == 422

    def test_toggle_task_status(self, client, new_task):
        """Test toggling a task flips between pending and completed."""
        task_id = client.post("/api/tasks", json=new_task).json()["id"]

        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "completed"
        assert client.patch(f"/api/tasks/{task_id}").json()["status"] == "pending"

    def test_delete_task(self, client, new_task):
        """Test deleting a task removes it from the list."""
        task_id = client.post("/api/tasks", json=new_task).json()["id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert task_id not in [t["id"] for t in client.get("/api/tasks").json()]

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_nonexistent_task(self, client, method):
        """Test toggling or deleting a task that doesn't exist."""
        response = getattr(client, method)("/api/tasks/nonexistent-task-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client, new_purchase_order):
        """Test creating a purchase order returns all fields with correct types."""
        response = client.post("/api/purchase-orders", json=new_purchase_order)
        assert response.status_code == 200

        po = response.json()
        assert po["id"].startswith("PO-")
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Components"
        assert isinstance(po["quantity"], int)
        assert isinstance(po["unit_cost"], (int, float))
        assert po["expected_delivery_date"] == "2026-11-15"
        assert po["status"] == "pending"
        assert po["notes"] == "Expedite if possible"
        assert "-" in po["created_date"]

    def test_get_purchase_order_by_backlog_item(self, client, new_purchase_order):
        """Test fetching the purchase order for a backlog item."""
        created = client.post("/api/purchase-orders", json=new_purchase_order).json()

        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_backlog_reflects_purchase_order(self, client, new_purchase_order):
        """Test that the backlog marks an item once a purchase order exists."""
        client.post("/api/purchase-orders", json=new_purchase_order)

        backlog = client.get("/api/backlog").json()
        item = next(b for b in backlog if b["id"] == "1")
        assert item["has_purchase_order"] is True

    def test_create_duplicate_purchase_order(self, client, new_purchase_order):
        """Test that a second purchase order for the same backlog item is rejected."""
        client.post("/api/purchase-orders", json=new_purchase_order)

        response = client.post("/api/purchase-orders", json=new_purchase_order)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client, new_purchase_order):
        """Test creating a purchase order for a backlog item that doesn't exist."""
        response = client.post(
            "/api/purchase-orders",
            json={**new_purchase_order, "backlog_item_id": "nonexistent-999"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.parametrize("override", [
        {"quantity": 0},
        {"quantity": -5},
        {"unit_cost": -1},
        {"supplier_name": ""},
        {"expected_delivery_date": "next week"},
    ])
    def test_create_purchase_order_invalid_input(self, client, new_purchase_order, override):
        """Test that invalid purchase order payloads are rejected with 422."""
        response = client.post("/api/purchase-orders", json={**new_purchase_order, **override})
        assert response.status_code == 422

    def test_get_nonexistent_purchase_order(self, client):
        """Test getting a purchase order for a backlog item without one."""
        response = client.get("/api/purchase-orders/nonexistent-999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
