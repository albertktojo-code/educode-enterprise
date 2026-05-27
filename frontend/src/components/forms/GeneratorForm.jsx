import { useState } from "react";

function GeneratorForm() {

    const [tema, setTema] = useState("");

    const [disciplina, setDisciplina] = useState("");

    const [estilo, setEstilo] = useState("Anime");

    const [resultado, setResultado] = useState("");

    const [imagens, setImagens] = useState([]);

    const [loading, setLoading] = useState(false);

    // ==========================================
    // GERAR CONTEÚDO
    // ==========================================

    async function gerarConteudo() {

        if (!tema) {

            setResultado("Digite um tema.");

            return;
        }

        setLoading(true);

        try {

            const response = await fetch(

                "http://127.0.0.1:8000/gerar-conteudo",

                {

                    method: "POST",

                    headers: {

                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({

                        tema,

                        disciplina,

                        estilo
                    })
                }
            );

            const data = await response.json();

            setResultado(data.resultado);

            setImagens(data.imagens || []);

        } catch (error) {

            setResultado(

                "Erro ao conectar ao backend."
            );
        }

        setLoading(false);
    }

    // ==========================================
    // UPLOAD
    // ==========================================

    async function uploadArquivo(event) {

        const arquivo = event.target.files[0];

        if (!arquivo) return;

        const formData = new FormData();

        formData.append("arquivo", arquivo);

        setLoading(true);

        try {

            const response = await fetch(

                "http://127.0.0.1:8000/gerar-upload",

                {

                    method: "POST",

                    body: formData
                }
            );

            const data = await response.json();

            setResultado(data.resultado);

            setImagens(data.imagens || []);

        } catch (error) {

            setResultado("Erro ao enviar arquivo.");
        }

        setLoading(false);
    }

    // ==========================================
    // EXPORTAR PDF
    // ==========================================

    function exportarPDF() {

        window.open(

            "http://127.0.0.1:8000/exportar-pdf",

            "_blank"
        );
    }

    return (

        <div
            style={{
                background: "#ffffff",
                padding: "35px",
                borderRadius: "25px",
                boxShadow: "0 8px 30px rgba(0,0,0,0.08)",
                marginBottom: "30px"
            }}
        >

            {/* HEADER */}

            <div
                style={{
                    marginBottom: "30px"
                }}
            >

                <h2
                    style={{
                        fontSize: "34px",
                        color: "#111827",
                        marginBottom: "10px"
                    }}
                >
                    Gerador Educacional IA
                </h2>

                <p
                    style={{
                        color: "#6b7280",
                        fontSize: "16px"
                    }}
                >
                    Plataforma inteligente para conteúdos,
                    HQs, jogos e materiais educacionais.
                </p>

            </div>

            {/* TEMA */}

            <input

                type="text"

                placeholder="Digite o tema"

                value={tema}

                onChange={(e) => setTema(e.target.value)}

                style={{

                    width: "100%",

                    padding: "16px",

                    borderRadius: "14px",

                    border: "1px solid #d1d5db",

                    marginBottom: "20px",

                    fontSize: "16px",

                    outline: "none"
                }}
            />

            {/* DISCIPLINA */}

            <select

                value={disciplina}

                onChange={(e) => setDisciplina(e.target.value)}

                style={{

                    width: "100%",

                    padding: "16px",

                    borderRadius: "14px",

                    border: "1px solid #d1d5db",

                    marginBottom: "20px",

                    fontSize: "16px",

                    outline: "none"
                }}
            >

                <option value="">
                    Selecione a disciplina
                </option>

                <option>
                    Matemática
                </option>

                <option>
                    Português
                </option>

                <option>
                    Ciências
                </option>

                <option>
                    História
                </option>

                <option>
                    Geografia
                </option>

                <option>
                    Programação
                </option>

                <option>
                    Inteligência Artificial
                </option>

            </select>

            {/* ESTILO */}

            <select

                value={estilo}

                onChange={(e) => setEstilo(e.target.value)}

                style={{

                    width: "100%",

                    padding: "16px",

                    borderRadius: "14px",

                    border: "1px solid #d1d5db",

                    marginBottom: "30px",

                    fontSize: "16px",

                    outline: "none"
                }}
            >

                <option>
                    Anime
                </option>

                <option>
                    Mangá
                </option>

                <option>
                    Cartoon
                </option>

                <option>
                    Pixel Art
                </option>

                <option>
                    HQ Americana
                </option>

                <option>
                    Cyberpunk
                </option>

                <option>
                    Minecraft
                </option>

                <option>
                    Roblox
                </option>

                <option>
                    Pokémon
                </option>

                <option>
                    Super Heróis
                </option>

                <option>
                    Medieval Fantasy
                </option>

            </select>

            {/* BOTÕES */}

            <div
                style={{
                    display: "flex",
                    gap: "15px",
                    flexWrap: "wrap",
                    marginBottom: "30px"
                }}
            >

                {/* GERAR */}

                <button

                    onClick={gerarConteudo}

                    style={{

                        background:
                            "linear-gradient(135deg,#2563eb,#1d4ed8)",

                        color: "#ffffff",

                        border: "none",

                        padding: "15px 28px",

                        borderRadius: "14px",

                        fontSize: "16px",

                        cursor: "pointer",

                        fontWeight: "bold",

                        boxShadow:
                            "0 4px 15px rgba(37,99,235,0.3)"
                    }}
                >

                    {

                        loading

                            ? "Gerando..."

                            : "Gerar Conteúdo IA"
                    }

                </button>

                {/* UPLOAD */}

                <label

                    style={{

                        background:
                            "linear-gradient(135deg,#10b981,#059669)",

                        color: "#ffffff",

                        padding: "15px 28px",

                        borderRadius: "14px",

                        cursor: "pointer",

                        fontWeight: "bold",

                        boxShadow:
                            "0 4px 15px rgba(16,185,129,0.3)"
                    }}
                >

                    Upload Arquivo

                    <input

                        type="file"

                        hidden

                        onChange={uploadArquivo}
                    />

                </label>

                {/* EXPORTAR PDF */}

                <button

                    onClick={exportarPDF}

                    style={{

                        background:
                            "linear-gradient(135deg,#ef4444,#dc2626)",

                        color: "#ffffff",

                        border: "none",

                        padding: "15px 28px",

                        borderRadius: "14px",

                        fontSize: "16px",

                        cursor: "pointer",

                        fontWeight: "bold",

                        boxShadow:
                            "0 4px 15px rgba(239,68,68,0.3)"
                    }}
                >

                    Exportar PDF

                </button>

            </div>

            {/* RESULTADO */}

            {

                resultado && (

                    <div
                        style={{

                            background: "#f9fafb",

                            padding: "25px",

                            borderRadius: "20px",

                            whiteSpace: "pre-wrap",

                            marginBottom: "30px",

                            lineHeight: "1.8",

                            border: "1px solid #e5e7eb"
                        }}
                    >

                        {resultado}

                    </div>
                )
            }

            {/* IMAGENS */}

            {

                imagens.length > 0 && (

                    <div>

                        <h3
                            style={{
                                marginBottom: "20px",
                                fontSize: "24px"
                            }}
                        >
                            Imagens Geradas
                        </h3>

                        <div
                            style={{

                                display: "grid",

                                gridTemplateColumns:
                                    "repeat(auto-fit, minmax(260px, 1fr))",

                                gap: "20px"
                            }}
                        >

                            {

                                imagens.map((img, index) => (

                                    <img

                                        key={index}

                                        src={img}

                                        alt="imagem"

                                        style={{

                                            width: "100%",

                                            borderRadius: "20px",

                                            objectFit: "cover",

                                            boxShadow:
                                                "0 6px 20px rgba(0,0,0,0.12)"
                                        }}
                                    />
                                ))
                            }

                        </div>

                    </div>
                )
            }

        </div>
    );
}

export default GeneratorForm;