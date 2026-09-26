# Karafun Player Control API Endpoints Reference

## WebSocket Connection

All communication occurs over a single WebSocket connection to `ws://[host]:57570/`.

---

## Client-to-Server Message Types

All messages are XML-formatted strings sent over the WebSocket.

### Player Control Messages

| Action Type | XML Format | Purpose |
| ------------- | ------------ | --------- |
| play | `<action type="play"></action>` | Start playback of current/paused song |
| pause | `<action type="pause"></action>` | Pause playback |
| next | `<action type="next"></action>` | Skip to next song in queue |
| seek | `<action type="seek">{seconds}</action>` | Seek to position in current song |
| pitch | `<action type="pitch">{value}</action>` | Adjust pitch (semitone shift) |
| tempo | `<action type="tempo">{value}</action>` | Adjust tempo (percentage) |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Query Messages

#### getStatus

**Request:**

```xml
<action type="getStatus" [noqueue]></action>
```

- `noqueue` is an optional attribute to skip queue data

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md)

#### getCatalogList

**Request:**

```xml
<action type="getCatalogList"></action>
```

Returns list of available catalogs (music libraries).

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

#### getList

**Request:**

```xml
<action type="getList" id="{list_id}" offset="{offset}" limit="{limit}"></action>
```

- `id`: Catalog ID (obtained from getCatalogList)
- `offset`: Starting position (optional, default: 0)
- `limit`: Maximum items (optional, default: 100)

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

#### search

**Request:**

```xml
<action type="search" offset="{offset}" limit="{limit}">{query}</action>
```

- `offset`, `limit`: Optional pagination
- `{query}`: Search string as inner text

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Volume Messages

#### setVolume

**Request:**

```xml
<action type="setVolume" volume_type="{type}">{volume}</action>
```

- `volume_type`: One of `general`, `bv`, `lead1`, `lead2`
- `volume`: Integer 0-100

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Queue Management Messages

#### clearQueue

**Request:**

```xml
<action type="clearQueue"></action>
```

#### addToQueue

**Request:**

```xml
<action type="addToQueue" song="{song_id}" singer="{singer}">{position}</action>
```

- `song_id`: Unique song identifier
- `singer`: Optional singer name (can be omitted)
- `position`: 0 (top), 1-n (specific), 99999 (bottom)

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

#### removeFromQueue

**Request:**

```xml
<action type="removeFromQueue" id="{position}"></action>
```

#### changeQueuePosition

**Request:**

```xml
<action type="changeQueuePosition" id="{old_position}">{new_position}</action>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Server-to-Client Response Messages

### Status Update (Polling or Push)

Clients can call `getStatus` or receive automatic status updates.

```xml
<status state="{state}">
  <position>{seconds}</position>
  <volumeList>
    <general>{volume}</general>
    <bv>{volume}</bv>
    <lead1 color="{hex}">{volume}</lead1>
    <lead2 color="{hex}">{volume}</lead2>
  </volumeList>
  <pitch>{value}</pitch>
  <tempo>{value}</tempo>
  <queue>
    <item id="{pos}" status="{status}">
      <title>{title}</title>
      <artist>{artist}</artist>
      <year>{year}</year>
      <duration>{seconds}</duration>
      <singer>{name}</singer>
    </item>
  </queue>
</status>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Catalog List Response

```xml
<catalogList>
  <catalog id="{id}" type="{type}">{caption}</catalog>
  ...
</catalogList>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Song List Response (getList/search)

```xml
<list total="{total}">
  <item id="{id}">
    <title>{title}</title>
    <artist>{artist}</artist>
    <year>{year}</year>
    <duration>{seconds}</duration>
  </item>
  ...
</list>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Catalog Types Reference

The `getCatalogList` response contains catalogs with these types:

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

## Player States Reference

| State | Description |
| ------- | ------------- |
| `idle` | Player is idle, no song playing |
| `infoscreen` | Information screen displayed |
| `loading` | Song data is loading |
| `playing` | Song is currently playing |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Queue Item States

| State | Description |
|-------|-------------|
| `ready` | Song is ready to play |
| `loading` | Song is loading buffers |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)
