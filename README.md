# IntentVerse

![Build Status](https://github.com/ngardiner/IntentVerse/actions/workflows/build-check.yml/badge.svg)

**IntentVerse is a dynamic, open-source AI MCP tool sandbox. It provides a safe and observable environment for developing, testing, and understanding AI agent/MCP tool interactions.**

## The Problem

As AI agents become more powerful, they need to interact with external tools like file systems, email, and web browsers to accomplish complex tasks. However, testing these agents presents a significant challenge:

* **Safety:** You cannot let an untested AI agent run loose on your real file system or email account.
* **Observability:** It's difficult to understand *what* an agent is trying to do. Logs of API calls are abstract and don't show the *consequences* of the agent's actions.
* **Reproducibility:** Setting up consistent, stateful testing environments is complex and time-consuming.

## Solution

IntentVerse solves these problems by creating a high-fidelity mock environment. It's a "padded room" for your AI, with a one-way mirror for you to watch through.

* **Safe Simulation:** IntentVerse exposes a suite of mock tools (like a virtual file system and email client) to your AI. The AI can write files, send emails, and perform other actions, but it's all safely contained within the simulation.
* **Visual Observability:** A clean, intuitive web interface shows you the *consequences* of your agent's actions in real-time. See the files being created, the emails being sent, and a human-readable audit log of every decision.
* **Dynamic & Modular:** Easily add new custom tools to the sandbox. The UI dynamically adapts to show your new tools without any frontend code changes.

---

### [ Placeholder for Screenshot of the IntentVerse UI ]

---

## Key Features

* **Secure User Authentication:** Standard JWT-based authentication for the web interface.
* **Schema-Driven UI:** A fully dynamic interface that renders based on the modules you have installed.
* **MCP Compliant:** Uses the standard Model Context Protocol (MCP) for communication with AI models.
* **Core Modules:** Comes with pre-built **File System**, **Email** and **Memory** modules.
* **Pluggable Tools:** Designed from the ground up to be modular and extensible.
* **External Logging:** Emits structured logs for easy integration with any observability platform.

## Getting Started

*(Placeholder for installation and setup instructions)*

```bash
# Example of how to run with Docker Compose
docker-compose up
