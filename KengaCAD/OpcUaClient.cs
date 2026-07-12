using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Opc.Ua;
using Opc.Ua.Client;

namespace KengaCAD
{
    /// <summary>OPC UA клиент для синхронизации I/O сигналов с PLC.</summary>
    public sealed class OpcUaClient : IDisposable
    {
        private Session? _session;
        private ApplicationConfiguration? _config;
        private readonly object _lock = new();

        public bool IsConnected
        {
            get
            {
                lock (_lock)
                    return _session?.Connected == true;
            }
        }

        public string? LastError { get; private set; }

        public async Task<bool> ConnectAsync(string endpointUrl, CancellationToken ct = default)
        {
            LastError = null;
            if (string.IsNullOrWhiteSpace(endpointUrl))
            {
                LastError = "Пустой endpoint OPC UA";
                return false;
            }

            try
            {
                await DisconnectAsync().ConfigureAwait(false);
                _config = await BuildConfigurationAsync().ConfigureAwait(false);
                var endpoint = CoreClientUtils.SelectEndpoint(_config, endpointUrl, useSecurity: false);
                var configured = new ConfiguredEndpoint(null, endpoint, EndpointConfiguration.Create(_config));

                var session = await Session.Create(
                    _config,
                    configured,
                    updateBeforeConnect: false,
                    checkDomain: false,
                    sessionName: "KengaCAD",
                    sessionTimeout: 60_000,
                    identity: new UserIdentity(new AnonymousIdentityToken()),
                    preferredLocales: null).ConfigureAwait(false);

                lock (_lock)
                {
                    _session?.Dispose();
                    _session = session;
                }
                return true;
            }
            catch (Exception ex)
            {
                LastError = ex.Message;
                return false;
            }
        }

        public Task DisconnectAsync()
        {
            lock (_lock)
            {
                if (_session != null)
                {
                    try
                    {
                        if (_session.Connected)
                            _session.Close();
                    }
                    catch { /* ignore */ }
                    _session.Dispose();
                    _session = null;
                }
            }
            return Task.CompletedTask;
        }

        public bool? ReadBool(string nodeId)
        {
            var v = ReadValue(nodeId);
            if (v == null) return null;
            try
            {
                if (v is bool b) return b;
                if (v is sbyte or byte or short or ushort or int or uint or long or ulong)
                    return Convert.ToInt64(v) != 0;
                return Convert.ToBoolean(v);
            }
            catch
            {
                return null;
            }
        }

        public bool WriteBool(string nodeId, bool value)
        {
            Session? session;
            lock (_lock) session = _session;
            if (session == null || !session.Connected || string.IsNullOrWhiteSpace(nodeId))
                return false;
            try
            {
                var node = new NodeId(nodeId);
                var writeValue = new WriteValue
                {
                    NodeId = node,
                    AttributeId = Attributes.Value,
                    Value = new DataValue(new Variant(value))
                };
                session.Write(
                    requestHeader: null,
                    nodesToWrite: new WriteValueCollection { writeValue },
                    results: out StatusCodeCollection results,
                    diagnosticInfos: out _);
                return StatusCode.IsGood(results[0]);
            }
            catch (Exception ex)
            {
                LastError = ex.Message;
                return false;
            }
        }

        public object? ReadValue(string nodeId)
        {
            Session? session;
            lock (_lock) session = _session;
            if (session == null || !session.Connected || string.IsNullOrWhiteSpace(nodeId))
                return null;
            try
            {
                var node = new NodeId(nodeId);
                var dv = session.ReadValue(node);
                return dv.Value;
            }
            catch (Exception ex)
            {
                LastError = ex.Message;
                return null;
            }
        }

        public IReadOnlyList<(string NodeId, string Name)> BrowseChildren(string nodeId = "i=85")
        {
            var result = new List<(string, string)>();
            Session? session;
            lock (_lock) session = _session;
            if (session == null || !session.Connected)
                return result;
            try
            {
                var node = new NodeId(nodeId);
                var refs = session.FetchReferences(node);
                foreach (var r in refs)
                {
                    if (NodeId.IsNull(r.NodeId)) continue;
                    try
                    {
                        var targetId = ExpandedNodeId.ToNodeId(r.NodeId, session.NamespaceUris);
                        if (NodeId.IsNull(targetId)) continue;
                        var target = session.ReadNode(targetId);
                        var name = target.DisplayName?.Text ?? r.BrowseName?.Name ?? targetId.ToString();
                        result.Add((targetId.ToString(), name));
                    }
                    catch { /* skip broken node */ }
                }
            }
            catch (Exception ex)
            {
                LastError = ex.Message;
            }
            return result;
        }

        private static async Task<ApplicationConfiguration> BuildConfigurationAsync()
        {
            var config = new ApplicationConfiguration
            {
                ApplicationName = "KengaCAD OPC UA Client",
                ApplicationUri = "urn:KengaCAD:OpcUaClient",
                ApplicationType = ApplicationType.Client,
                SecurityConfiguration = new SecurityConfiguration
                {
                    AutoAcceptUntrustedCertificates = true,
                    RejectSHA1SignedCertificates = false,
                    MinimumCertificateKeySize = 1024,
                    ApplicationCertificate = new CertificateIdentifier
                    {
                        StoreType = CertificateStoreType.Directory,
                        StorePath = "%CommonApplicationData%\\KengaCAD\\pki\\own",
                        SubjectName = "CN=KengaCAD OPC UA Client"
                    },
                    TrustedIssuerCertificates = new CertificateTrustList
                    {
                        StoreType = CertificateStoreType.Directory,
                        StorePath = "%CommonApplicationData%\\KengaCAD\\pki\\issuer"
                    },
                    TrustedPeerCertificates = new CertificateTrustList
                    {
                        StoreType = CertificateStoreType.Directory,
                        StorePath = "%CommonApplicationData%\\KengaCAD\\pki\\trusted"
                    },
                    RejectedCertificateStore = new CertificateTrustList
                    {
                        StoreType = CertificateStoreType.Directory,
                        StorePath = "%CommonApplicationData%\\KengaCAD\\pki\\rejected"
                    }
                },
                TransportQuotas = new TransportQuotas { OperationTimeout = 15_000 },
                ClientConfiguration = new ClientConfiguration { DefaultSessionTimeout = 60_000 },
                TraceConfiguration = new TraceConfiguration()
            };
            await config.Validate(ApplicationType.Client).ConfigureAwait(false);
            config.CertificateValidator.CertificateValidation += (_, e) => e.Accept = e.Error.StatusCode != StatusCodes.BadCertificateUseNotAllowed;
            return config;
        }

        public void Dispose()
        {
            DisconnectAsync().GetAwaiter().GetResult();
        }
    }
}
