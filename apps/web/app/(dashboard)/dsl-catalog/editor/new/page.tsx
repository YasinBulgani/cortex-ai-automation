import { DslActionEditor } from "@/components/dsl/DslActionEditor";

export const metadata = {
  title: "Yeni DSL Cümleciği — Neurex",
  description: "Yeni bir test DSL cümleciği oluştur.",
};

export default function NewDslActionPage() {
  return <DslActionEditor mode="create" />;
}
