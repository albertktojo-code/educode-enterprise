import GeneratorForm from "../components/forms/GeneratorForm";
import ProjectHistory from "../components/ProjectHistory";

function Dashboard() {

    return (

        <div
            style={{
                minHeight: "100vh",
                background: "#f4f7fb",
                padding: "40px",
                fontFamily: "Arial"
            }}
        >

            <div
                style={{
                    maxWidth: "1200px",
                    margin: "0 auto"
                }}
            >

                <div
                    style={{
                        background: "#ffffff",
                        padding: "30px",
                        borderRadius: "20px",
                        marginBottom: "30px",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.08)"
                    }}
                >

                    <h1
                        style={{
                            fontSize: "40px",
                            marginBottom: "10px"
                        }}
                    >
                        Educode Enterprise
                    </h1>

                    <p
                        style={{
                            color: "#666",
                            fontSize: "18px"
                        }}
                    >
                        Plataforma de geração de conteúdos educacionais com IA
                    </p>

                </div>

                <GeneratorForm />

                <ProjectHistory />

            </div>

        </div>
    );
}

export default Dashboard;