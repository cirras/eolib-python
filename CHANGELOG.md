# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-06-30

### Added

- `SpellReplyServerPacket` packet class.
- `SkillStatRequirements` class.
- `PlayerEffect` class.
- `TileEffect` class.
- `EffectPlayerServerPacket.effects` field.
- `EffectAgreeServerPacket.effects` field.
- `AdminInteractTellServerPacket.gold_bank` field.

### Changed

- Make protocol objects immutable.
  - Protocol data structures are now fully instantiated via `__init__`, and can't be modified later.
  - Array fields are now typed as tuples.
- Rename `QuestReportServerPacket.npc_id` field to `npc_index`.
- Make `CastReplyServerPacket.caster_tp` field optional.
- Make `CastSpecServerPacket.caster_tp` field optional.
- Make `CastAcceptServerPacket.caster_tp` field optional.
- Make `CastAcceptServerPacket.experience` field optional.
- Make `CastAcceptServerPacket.level_up` field optional.
- Make `NpcAcceptServerPacket.experience` field optional.
- Make `NpcAcceptServerPacket.level_up` field optional.
- Change `TradeItemData` to represent a single player's trade items instead of both trade partners.
- Change `TradeReplyServerPacket.trade_data` field type from `TradeItemData` to `TradeItemData[]`.
- Change `TradeAdminServerPacket.trade_data` field type from `TradeItemData` to `TradeItemData[]`.
- Change `TradeUseServerPacket.trade_data` field type from `TradeItemData` to `TradeItemData[]`.

### Removed

- All protocol object field setters.
- `EffectPlayerServerPacket.player_id` field.
- `EffectPlayerServerPacket.effect_id` field.
- `EffectAgreeServerPacket.coords` field.
- `EffectAgreeServerPacket.effect_id` field.
- `WalkPlayerServerPacket.Direction` field.

### Fixed

- Fix incorrect (de)serialization of `EffectPlayerServerPacket` due to only the first effect in the
  array being recognized.
- Fix incorrect (de)serialization of `EffectAgreeServerPacket` due to only the first effect in the
  array being recognized.
- Fix inaccurate serialization of `QuestAcceptClientPacket` where the char value 0 should be written
  for `DialogReply.Ok`.
- Fix inaccurate serialization of `AccountReplyServerPacket` where the string value "OK" should be
  written for `AccountReply.Changed`, but "NO" was being written instead.
- Fix inaccurate serialization of `AdminInteractTellServerPacket` where the `gold_bank` field was
  missing.
- Fix inaccurate serialization of `RecoverPlayerServerPacket` where a trailing 0 short value was
  missing.
- Fix inaccurate serialization of `ShopOpenServerPacket` where a trailing break byte was erroneously
  being written.
- Fix inaccurate serialization of `DoorOpenServerPacket` where a trailing 0 char value was
  erroneously being written.
- Change incorrect `CharacterStatsInfoLookup.secondary_stats` field type from
  `CharacterSecondaryStats` to `CharacterSecondaryStatsInfoLookup`.
- Change incorrect `SkillLearn.stat_requirements` field type from `CharacterBaseStats` to
  `SkillStatRequirements`.

## [1.2.0] - 2025-06-30

### Added

- Support for Python 3.13.
- Support for Python 3.14.
- Support for server pub files:
  - `DropRecord` class.
  - `DropNpcRecord` class.
  - `DropFile` class.
  - `InnQuestionRecord` class.
  - `InnRecord` class.
  - `InnFile` class.
  - `SkillMasterSkillRecord` class.
  - `SkillMasterRecord` class.
  - `SkillMasterFile` class.
  - `ShopTradeRecord` class.
  - `ShopCraftIngredientRecord` class.
  - `ShopCraftRecord` class.
  - `ShopRecord` class.
  - `ShopFile` class.
  - `TalkMessageRecord` class.
  - `TalkRecord` class.
  - `TalkFile` class.
- `GuildTakeClientPacket.guild_tag` field.

### Fixed

- Fix bug on Python 3.13+ where any protocol enum instance constructed from an int value would be
  treated like an unrecognized value.
- Fix `AttributeError` on Python 3.14 because the readonly `__doc__` attribute was being assigned to
  in generated protocol code.
- Fix incorrect (de)serialization of some data structures containing arrays with trailing delimiters.
- Fix incorrect (de)serialization of data structures containing both `<dummy>` and `<field>` elements.
  (Only `ChestCloseServerPacket` was impacted.)
- Fix incorrect (de)serialization of `NpcAgreeServerPacket` due to the `npcs` array's length being
  treated as a `short` instead of `char`.
- Fix incorrect (de)serialization of `GuildTakeClientPacket` due to missing `guild_tag` field.
- Fix incorrect (de)serialization of `AvatarAdminServerPacket` due to incorrect ordering of the
  `caster_direction` and `damage` fields.
- Fix inaccurate (de)serialization of `JukeboxMsgClientPacket` due to the packet being treated as a
  chunked data structure.
- Sanitize strings within chunked sections of protocol data structures.
  - Generated code now sets `EoWriter.string_sanitization_mode` during serialization.
  - For more information, see
    [Chunked Reading: Sanitization](https://github.com/Cirras/eo-protocol/blob/master/docs/chunks.md#sanitization).
- Properly escape characters from the upsteam protocol XML in docstrings and downstream generated documentation.

## [1.1.1] - 2024-08-22

### Changed

- The package is now [PEP 561](https://peps.python.org/pep-0561/) compatible, exposing type
  information for usage in type checkers like
  [mypy](https://mypy.readthedocs.io/en/stable/index.html).

## [1.1.0] - 2023-12-19

### Added

- `WalkPlayerServerPacket.direction` field.

### Changed

- Remove trailing break from `ArenaSpecServerPacket`.
- Remove trailing break from `ArenaAcceptServerPacket`.
- Deprecate `WalkPlayerServerPacket.Direction` field.

## [1.0.0] - 2023-11-07

### Added

- Support for EO data structures:
  - Client packets
  - Server packets
  - Endless Map Files (EMF)
  - Endless Item Files (EIF)
  - Endless NPC Files (ENF)
  - Endless Spell Files (ESF)
  - Endless Class Files (ECF)
- Utilities:
  - Data reader
  - Data writer
  - Number encoding
  - String encoding
  - Data encryption
  - Packet sequencer

[Unreleased]: https://github.com/cirras/eolib-python/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/cirras/eolib-python/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/cirras/eolib-python/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/cirras/eolib-python/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/cirras/eolib-python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/cirras/eolib-python/releases/tag/v1.0.0