# -*- coding: utf-8 -*-
"""
Models module for AI Coordination Engine.

This module contains PynamoDB models for data persistence:
- CoordinationModel: AI coordination configurations
- SessionModel: User session management
- SessionAgentModel: Agent execution within sessions
- SessionRunModel: Session execution history
- TaskModel: Task definitions and metadata
- TaskScheduleModel: Task scheduling configurations

Includes batch_loaders for optimized GraphQL DataLoader pattern.
"""
from __future__ import print_function

__author__ = "bibow"
