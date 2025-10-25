# Module Dependency Diagram

## Layered Architecture

```mermaid
graph TD
    scripts[Scripts CLI Layer]
    reporting[Reporting Layer]
    backtesting[Backtesting Layer]
    portfolio[Portfolio Layer]
    analytics[Analytics Layer]
    assets[Assets Layer]
    data[Data Layer]
    core[Core Layer]
    macro[Macro Module]

    scripts --> reporting
    scripts --> backtesting
    scripts --> portfolio
    scripts --> analytics
    scripts --> assets
    scripts --> data
    scripts --> core
    scripts --> macro

    reporting --> backtesting
    reporting --> portfolio
    reporting --> core

    backtesting --> portfolio
    backtesting --> analytics
    backtesting --> assets
    backtesting --> data
    backtesting --> core

    portfolio --> analytics
    portfolio --> assets
    portfolio --> data
    portfolio --> core

    analytics --> assets
    analytics --> data
    analytics --> core

    assets --> data
    assets --> core

    data --> core

    macro --> data
    macro --> core

    style core fill:#90EE90
    style data fill:#ADD8E6
    style assets fill:#FFB6C1
    style analytics fill:#FFFFE0
    style portfolio fill:#FFD700
    style backtesting fill:#FFA500
    style reporting fill:#FF6347
    style scripts fill:#DDA0DD
    style macro fill:#D3D3D3
```

## Dependency Rules

**Green (Core):** No dependencies
**Blue (Data):** Depends only on core
**Pink (Assets):** Depends on data, core
**Yellow (Analytics):** Depends on assets, data, core
**Gold (Portfolio):** Depends on analytics, assets, data, core
**Orange (Backtesting):** Depends on portfolio and below
**Red (Reporting):** Depends on backtesting, portfolio (top layer)
**Purple (Scripts):** Can depend on everything (orchestration)
**Gray (Macro):** Minimal dependencies (stub module)

## Key Constraints

1. **No circular dependencies** - Enforced by import-linter
2. **Lower layers don't depend on higher layers** - Enforced
3. **Core is self-contained** - Enforced
4. **Backtesting doesn't know about reporting** - Enforced

## Validation

```bash
lint-imports --config .importlinter
```
