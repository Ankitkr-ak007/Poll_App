def test_login(client):
    response = client.post("/api/admin/login", json={"username": "testadmin", "password": "testpass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_and_manage_poll(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get initial draft poll
    response = client.get("/api/admin/poll", headers=headers)
    assert response.status_code == 200
    poll = response.json()
    assert poll["status"] == "draft"
    
    # Update poll
    response = client.put("/api/admin/poll", headers=headers, json={
        "question": "Is this a test?",
        "option_a_text": "Yes",
        "option_b_text": "No"
    })
    assert response.status_code == 200
    assert response.json()["question"] == "Is this a test?"

def test_add_participants_and_vote(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Add participants
    response = client.post("/api/admin/participants", headers=headers, json={"names": ["Alice", "Bob"]})
    assert response.status_code == 200
    participants = response.json()
    assert len(participants) == 2
    
    # Open poll
    response = client.post("/api/admin/poll/open", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    
    # Public poll check
    response = client.get("/api/poll")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    
    # Participant search
    response = client.get("/api/participants/search?q=A")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Alice"
    alice_id = results[0]["id"]
    
    # Vote successfully
    response = client.post("/api/vote", json={"participant_id": alice_id, "option": "A"})
    assert response.status_code == 200
    
    # Double vote attempt
    response = client.post("/api/vote", json={"participant_id": alice_id, "option": "B"})
    assert response.status_code == 409
    
    # Close poll
    response = client.post("/api/admin/poll/close", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    
    # Voting on inactive poll
    bob = next(p for p in participants if p["name"] == "Bob")
    response = client.post("/api/vote", json={"participant_id": bob["id"], "option": "B"})
    assert response.status_code == 403
    
    # Results check
    response = client.get("/api/admin/results", headers=headers)
    assert response.status_code == 200
    results = response.json()
    assert results["total"] == 1
    assert results["option_a"]["count"] == 1
    assert results["option_b"]["count"] == 0
    
    # Reset poll
    response = client.post("/api/admin/poll/reset", headers=headers, json={"confirm": True})
    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    
    # Check that votes were cleared
    response = client.get("/api/admin/results", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 0
