# Implementation Plan: Ledger Service

## Summary

The Ledger Service manages financial accounts and transactions for the PersonalFinance platform. It depends on Identity Service for authentication and authorization.

## Technical Context

**Language/Version**: C# / .NET 8
**Primary Dependencies**: EF Core 8, FluentValidation, AutoMapper, MassTransit
**Storage**: PostgreSQL (per-service database)
**Testing**: xUnit, Testcontainers, Pact

## Design Decisions

### D1: Domain Model

Account and Transaction entities with value objects for Money, Currency.

### D2: Repository Pattern

Interface-based repositories with EF Core implementations.

### D3: Service Layer

Application services with FluentValidation for input validation and AutoMapper for DTO mapping.
