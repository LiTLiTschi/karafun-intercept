# Karafun Player Control API Data Formats

## Message Format

All API messages use **XML** format transmitted over WebSocket.

### Character Encoding

- UTF-8 encoding is used (standard for XML)
- Special characters should be escaped: `&`, `<`, `>`, `"`, `'`

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md) - "Colors are in HTML format #RRGGBB" (implying encoding considerations for XML)

---

## Song Metadata Fields

### Song List Items (`list`/`item` response)

| Field | Type | Description | Location |
| ------- | ------ | ------------- | ---------- |
| `id` | string (integer) | Unique song identifier | Attribute: `id` |
| `title` | string | Song title | Element: `<title>` |
| `artist` | string | Artist name | Element: `<artist>` |
| `year` | string | Release year | Element: `<year>` |
| `duration` | string (seconds) | Duration in seconds | Element: `<duration>` |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - Response format for `getList` and `search`

### Queue Items (`queue`/`item` response)

| Field | Type | Description | Location |
| ------- | ------ | ------------- | ---------- |
| `id` | integer | Queue position | Attribute: `id` |
| `status` | enum | Queue item state | Attribute: `status` |
| `title` | string | Song title | Element: `<title>` |
| `artist` | string | Artist name | Element: `<artist>` |
| `year` | string | Release year | Element: `<year>` |
| `duration` | string (seconds) | Duration in seconds | Element: `<duration>` |
| `singer` | string | Singer name (user-assigned) | Element: `<singer>` |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - Response format for `getStatus`

---

## Player State Format

### Status Response

```xml
<status state="{state}">
  <position>{seconds}</position>
  <volumeList>
    <general caption="{caption}">{volume}</general>
    <bv caption="{caption}">{volume}</bv>
    <lead1 color="{hex}">{volume}</lead1>
    <lead2 color="{hex}">{volume}</lead2>
  </volumeList>
  <pitch>{value}</pitch>
  <tempo>{value}</tempo>
  <queue>
    <item id="{pos}" status="{status}">...</item>
  </queue>
</status>
```

| Field | Type | Description |
| ------- | ------ | ------------- |
| `state` | enum | Player state (`idle`, `infoscreen`, `loading`, `playing`) |
| `position` | integer | Current position in seconds |
| `volumeList` | object | Volume controls |
| `pitch` | integer | Pitch adjustment value |
| `tempo` | integer | Tempo percentage |
| `queue` | object | Queue items |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Volume List Format

### Volume Items

| Element | Attributes | Description |
| --------- | ------------ | ------------- |
| `general` | `caption` | Main volume control |
| `bv` | `caption` | Backing vocals volume |
| `lead1` | `caption`, `color` | Lead vocal 1 volume |
| `lead2` | `caption`, `color` | Lead vocal 2 volume |

**Volume Range:** 0-100 (0 = muted, 100 = full volume)

**Color Format:** HTML hex format `#RRGGBB`

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - "Volume values are between 0 (muted) and 100 (full volume)"

---

## Catalog Format

### Catalog List Response

```xml
<catalogList>
  <catalog id="{id}" type="{type}">{caption}</catalog>
</catalogList>
```

| Field | Type | Description |
| ------- | ------ | ------------- |
| `id` | integer | Unique catalog identifier |
| `type` | enum | Catalog type (see types table) |
| `caption` | string | Display name |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Catalog Types

| Type | Description |
| ------ | ------------- |
| `onlineComplete` | Complete online catalog |
| `onlineNews` | Recently added songs |
| `onlineFavorites` | User favorited songs |
| `onlineStyle` | Genre/style-based catalogs |
| `localPlaylist` | Locally created playlists |
| `localDirectory` | Local file directory |

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md) - "type possible values"

---

## Player States

| State | Description |
| ------- | ------------- |
| `idle` | No song playing |
| `infoscreen` | Information screen active |
| `loading` | Song data loading |
| `playing` | Song currently playing |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Queue Item States

| State | Description |
|-------|-------------|
| `ready` | Song ready to play |
| `loading` | Song buffers loading |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Special Characters and Escaping

XML special characters must be escaped when included in text content:

| Character | Escape Sequence |
| ----------- | ----------------- |
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |
| `'` | `&apos;` |

Source: [karafun/touch javascript implementations](https://github.com/karafun/touch/blob/master/i/js/tcpclient.js) - Character escaping patterns observed

### Escape Examples

From `karafun-touch/i/js/tcpclient.js`:

```javascript
singer = singer.replace(/&/g, '&amp;')
       .replace(/</g, '&lt;')
       .replace(/>/g, '&gt;')
       .replace(/"/g, '&quot;')
       .replace(/'/g, '&apos;');
```

Source: [recisio/karafun-touch/tcpclient.js](https://github.com/recisio/karafun-touch/blob/master/i/js/tcpclient.js)

From `karasocket/src/karafunXml.js`:

```javascript
.replace(/&apos;/g, "'")
.replace(/&quot;/g, '"')
.replace(/&gt;/g, '>')
.replace(/&lt;/g, '<')
.replace(/&amp;/g, '&')
```

Source: [jon-toy/karasocket/src/karafunXml.js](https://github.com/jon-toy/karasocket/blob/master/src/karafunXml.js) - Response parsing with unescape

---

## Data Types Summary

| Field | Data Type | Format |
| ------- | ----------- | -------- |
| song_id, catalog_id | integer | Unquoted, in attributes |
| position (time) | float | Unquoted, in elements |
| volume | integer | 0-100, unquoted |
| pitch | integer | Semitone value, unquoted |
| tempo | integer | Percentage 0-100, unquoted |
| artist, title, singer | string | XML escaped in elements |
| color | string | Hex format `#RRGGBB` in attributes |

---

## Unverified Metadata Claims

The following metadata fields are **NOT documented in the available sources** and have not been verified:

- `key` (musical key, e.g., C, G#m)
- `bpm` (beats per minute)
- `tempo` as tempo percentage (mentioned but not detailed)
- Video stream URLs
- Lyrics/syllable synchronization data
- Separate lead/backing vocal control beyond volume levels
- Song difficulty levels
- Genre/style tags

**Note:** These may be available in Karafun's premium API (Box/OEM) but not in the Player Control API.
