import sys
import os
import signal
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

def get_connector():
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.gnome.Mutter.DisplayConfig",
            "/org/gnome/Mutter/DisplayConfig",
            "org.gnome.Mutter.DisplayConfig",
            None
        )
        state = proxy.call_sync("GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None)
        unpacked = state.unpack()
        monitors = unpacked[1]
        if len(monitors) > 0:
            spec = monitors[0][0]
            connector = spec[0]
            return connector
    except Exception as e:
        print(f"DEBUG Error getting connector: {e}", file=sys.stderr)
    return "HDMI-1"

def main():
    loop = GLib.MainLoop()
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    
    screencast_proxy = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.gnome.Mutter.ScreenCast",
        "/org/gnome/Mutter/ScreenCast",
        "org.gnome.Mutter.ScreenCast",
        None
    )
    
    res = screencast_proxy.call_sync(
        "CreateSession",
        GLib.Variant('(a{sv})', [{}]),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    session_path = res.unpack()[0]
    
    session_proxy = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.gnome.Mutter.ScreenCast",
        session_path,
        "org.gnome.Mutter.ScreenCast.Session",
        None
    )
    
    connector = get_connector()
    print(f"DEBUG: Using monitor connector: {connector}", file=sys.stderr)
    
    res = session_proxy.call_sync(
        "RecordMonitor",
        GLib.Variant('(sa{sv})', (connector, {'cursor-mode': GLib.Variant('u', 1)})),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    stream_path = res.unpack()[0]
    
    def on_signal(connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
        if signal_name == "PipeWireStreamAdded":
            node_id = parameters.unpack()[0]
            print(f"NODE_ID:{node_id}", flush=True)
            print(f"DEBUG: PipeWire stream added with Node ID: {node_id}", file=sys.stderr)
            
    bus.signal_subscribe(
        "org.gnome.Mutter.ScreenCast",
        "org.gnome.Mutter.ScreenCast.Stream",
        "PipeWireStreamAdded",
        stream_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_signal,
        None
    )
    
    # Start the session *after* subscribing to the signal
    session_proxy.call_sync(
        "Start",
        None,
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    print("DEBUG: Session Start called", file=sys.stderr)
    
    def sig_handler(sig, frame):
        loop.quit()
        
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    
    loop.run()

if __name__ == '__main__':
    main()
