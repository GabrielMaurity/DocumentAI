using System.Reflection;
using Microsoft.OpenApi;
using Scalar.AspNetCore;

namespace DocumentAI.API.OpenApi;

/// <summary>
/// Registra e expõe a documentação web da API: o documento OpenAPI e a interface do Scalar.
/// </summary>
internal static class DocumentacaoApiExtensions
{
    private const string NomeDocumento = "v1";
    private const string RecursoDescricao = "DocumentAI.API.OpenApi.descricao-api.md";

    /// <summary>
    /// Registra a geração do documento OpenAPI com título, versão e descrição detalhada.
    /// </summary>
    public static IServiceCollection AddDocumentacaoApi(this IServiceCollection services)
    {
        var descricao = LerDescricao();

        services.AddOpenApi(NomeDocumento, options =>
        {
            options.AddDocumentTransformer((document, _, _) =>
            {
                document.Info = new OpenApiInfo
                {
                    Title = "DocumentAI API",
                    Version = "v1",
                    Description = descricao,
                };

                // Sem servidores fixos, o Scalar usa a origem da própria página.
                // Assim, "Try it" funciona igual em DEV e em PROD, inclusive atrás do proxy HTTPS do App Service.
                document.Servers = [];

                return Task.CompletedTask;
            });
        });

        return services;
    }

    /// <summary>
    /// Mapeia <c>/openapi/v1.json</c> e a interface do Scalar em <c>/scalar</c>.
    /// </summary>
    public static WebApplication MapDocumentacaoApi(this WebApplication app)
    {
        app.MapOpenApi();

        app.MapScalarApiReference(options =>
        {
            options.Title = "DocumentAI API — Documentação";
            options.Theme = ScalarTheme.Purple;
            options.DefaultHttpClient = new(ScalarTarget.Shell, ScalarClient.Curl);
            options.HideModels = false;

            // Página voltada a testes da API: sem os recursos de nuvem da Scalar
            // (ferramentas de desenvolvedor, assistente de IA, MCP, geração de SDK) e sem telemetria.
            options.ShowDeveloperTools = DeveloperToolsVisibility.Never;
            options.Agent = new ScalarAgentOptions { Disabled = true };
            options.Mcp = new ScalarMcpOptions { Disabled = true };
            options.HideClientButton = true;
            options.Telemetry = false;
        });

        return app;
    }

    private static string LerDescricao()
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(RecursoDescricao)
            ?? throw new InvalidOperationException($"Recurso incorporado '{RecursoDescricao}' não encontrado.");
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd();
    }
}
