export default function StatusIndicator({ label, service }) {
  return <span className={`status ${service?.available ? 'online' : 'offline'}`} title={service?.message || 'Checking connection'}><span/>{label}<small>{service ? service.available ? 'Connected' : 'Unavailable' : 'Checking'}</small></span>;
}
