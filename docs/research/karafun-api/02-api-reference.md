# Karafun Player Control API Reference

## Communication Protocol

| Aspect | Value |
| -------- | ------- |
| Transport | WebSocket (TCP) |
| Default Port | `57570` |
| URL Format | `ws://[host]:57570/` |
| Message Format | XML over WebSocket |
| Message Type | Actions (client --> server), Status/List updates (server --> client) |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - "Communications between your software and KaraFun Player are made through TCP WebSockets"

---

## Action Requests (Client to Server)

### Connection Management

No explicit connect action - connection is established when WebSocket opens.

---

### Player Control Actions

| Action | Syntax | Description |
| -------- | -------- | ------------- |
| Play | `<action type="play"></action>` | Start playback |
| Pause | `<action type="pause"></action>` | Pause playback |
| Next | `<action type="next"></action>` | Skip to next song |
| Seek | `<action type="seek">{seconds}</action>` | Seek to position in seconds (float supported) |
| Pitch | `<action type="pitch">{pitch}</action>` | Set pitch value (integer) |
| Tempo | `<action type="tempo">{tempo}</action>` | Set tempo value (percentage as integer) |

Source: [Official archived action list](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Query Actions

### Get Status

**Request:**

```xml
<action type="getStatus" [noqueue]></action>
```

Parameter `noqueue` is optional - when included, the response omits queue information.

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md)

**Response:**

```xml
<status state="{player_state}">
  [<position>{time_in_seconds}</position>]
  <volumeList>
    <general caption="{caption}">{volume}</general>
    [<bv caption="{caption}">{volume}</bv>]
    [<lead1 caption="{caption}" color="{color}">{volume}</lead1>]
    [<lead2 caption="{caption}" color="{color}">{volume}</lead2>]
  </volumeList>
  <pitch>{pitch}</pitch>
  <tempo>{tempo}</tempo>
  <queue>
    <item id="{queue_position}" status="{item_state}">
      <title>{song_name}</title>
      <artist>{artist_name}</artist>
      <year>{year}</year>
      <duration>{duration_in_seconds}</duration>
      [<singer>{singer_name}</singer>]
    </item>
    ...
  </queue>
</status>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Get Catalog List

**Request:**

```xml
<action type="getCatalogList"></action>
```

**Response:**

```xml
<catalogList>
  <catalog id="{unique_id}" type="{type}">{caption}</catalog>
  ...
</catalogList>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Get List Content

**Request:**

```xml
<action type="getList" id="{list_id}" offset="{offset}" limit="{limit}"></action>
```

- `offset` and `limit` are optional (default limit: 100)
- Returns songs from a specific catalog

**Response:**

```xml
<list total={total}>
  <item id="{unique_id}">
    <title>{song_name}</title>
    <artist>{artist_name}</artist>
    <year>{year}</year>
    <duration>{duration_in_seconds}</duration>
  </item>
  ...
</list>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

### Search

**Request:**

```xml
<action type="search" offset="{offset}" limit="{limit}">{search_string}</action>
```

- `offset` and `limit` are optional (default limit: 100)
- Search string is the inner text of the action element

**Response:**
Same format as `getList` response:

```xml
<list total={total}>
  <item id="{unique_id}">...</item>
</list>
```

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Volume Management

### Set Volume

**Request:**

```xml
<action type="setVolume" volume_type="{volume_type}">{volume}</action>
```

- `volume_type`: `general`, `bv`, `lead1`, `lead2`
- `volume`: Integer 0-100 (0 = muted, 100 = full)

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Song Queue Management

| Action | Syntax | Description |
| -------- | -------- | ------------- |
| Clear Queue | `<action type="clearQueue"></action>` | Remove all songs from queue |
| Add to Queue | `<action type="addToQueue" song="{song_id}" singer="{singer_name}">{position}</action>` | Add song at position |
| Remove from Queue | `<action type="removeFromQueue" id="{queue_position}"></action>` | Remove song by position |
| Change Position | `<action type="changeQueuePosition" id="{old_position}">{new_position}</action>` | Move song to new position |

**Position values:**

- `0`: Top of queue
- `1...n`: Specific position
- `99999`: Bottom of queue

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Screen Management

| Action | Syntax | Description |
|--------|--------|-------------|
| Set Position | `<action type="screenPosition" x="{x}" y="{y}" width="{width}" height="{height}"></action>` | Set screen coordinates |
| Fullscreen | `<action type="fullscreen"></action>` | Put second screen in fullscreen |

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md)

---

## Response Parsing

All responses are XML documents that can be parsed with standard XML parsers.

**Common patterns observed in implementations:**

- JavaScript (karasocket): Uses `xml-js` library for `xml2js`
- Java (AndroidKarafunAPI): Uses `XmlPullParser`
- JavaScript (karafun-touch): Uses `.parseXML()` with jQuery

Source: [jon-toy/karasocket/src/websocket.js](https://github.com/jon-toy/karasocket/blob/master/src/websocket.js)

---

## API Constants from Source Code

### Catalog Types (from karafun/touch source)

```javascript
// From src/constants.js equivalent patterns
type possible values :
* onlineComplete
* onlineNews
* onlineFavorites
* onlineStyle
* localPlaylist
* localDirectory
```

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md) - "type possible values"

### Player States (from responses)

```xml
<status state="{player_state}">
```

Possible `player_state` values:

- `idle`
- `infoscreen`
- `loading`
- `playing`

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

### Item States (in queue items)

Possible `status` attribute values on `<item>`:

- `ready`
- `loading`

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Implementation Examples

### Node.js (natelewis/karafun-api)

**File:** `lib/karafun-api.js`

- WebSocket client using `websocket` package
- Default host: `localhost`, port: `57570`
- Emits events: `connecting`, `connected`, `closed`, `connectionFailed`, `connectionError`, `statusUpdated`, `playStarted`, `playStopped`

Source: [natelewis/karafun-api/lib/karafun-api.js](https://github.com/natelewis/karafun-api/blob/master/lib/karafun-api.js)

### React/JavaScript (jon-toy/karasocket)

**File:** `src/websocket.js`

- Uses native WebSocket API
- Parses XML responses with `xml-js`
- Handles: `status.queue`, `status.state`, `list` responses

Source: [jon-toy/karasocket/src/websocket.js](https://github.com/jon-toy/karasocket/blob/master/src/websocket.js)

### Java (AndroidKarafunAPI)

**File:** `KarafunClient.java`

- Uses OkHttp for WebSocket
- Structured client with methods: `getStatus()`, `getCatalogList()`, `getList()`, `search()`, `play()`, `pause()`, `next()`, `seek()`, `pitch()`, `tempo()`, `setVolume()`, `addToQueue()`, `removeFromQueue()`, `changeQueuePosition()`, `clearQueue()`

Source: [polytope/AndroidKarafunAPI/KarafunClient.java](https://github.com/polytope/AndroidKarafunAPI/blob/master/src/main/java/dk/polytope/androidkarafunapi/KarafunClient.java)
