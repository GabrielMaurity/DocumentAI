using DocumentAI.API.OpenApi;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddDocumentacaoApi();

var app = builder.Build();

app.UseHttpsRedirection();

// Documentação web (OpenAPI + Scalar) disponível em todos os ambientes.
app.MapDocumentacaoApi();

app.MapControllers();

app.Run();
