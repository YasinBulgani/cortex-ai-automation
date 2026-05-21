import { DslActionEditor } from "@/components/dsl/DslActionEditor";

export const metadata = {
  title: "Yeni DSL Cümleciği — TestwrightAI",
  description: "Yeni bir test DSL cümleciği oluştur.",
};

export default function NewDslActionPage() {
  return <DslActionEditor mode="create" />;
}
