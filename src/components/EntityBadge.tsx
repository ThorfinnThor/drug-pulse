import { Building2, Pill, FlaskConical, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface EntityBadgeProps {
  type: 'company' | 'drug' | 'trial' | 'indication';
  size?: 'sm' | 'md' | 'lg';
}

const entityConfig = {
  company: {
    icon: Building2,
    label: 'Company',
    className: 'bg-pharma-blue/10 text-pharma-blue border-pharma-blue/20 hover:bg-pharma-blue/20'
  },
  drug: {
    icon: Pill,
    label: 'Drug',
    className: 'bg-pharma-green/10 text-pharma-green border-pharma-green/20 hover:bg-pharma-green/20'
  },
  trial: {
    icon: FlaskConical,
    label: 'Trial',
    className: 'bg-pharma-orange/10 text-pharma-orange border-pharma-orange/20 hover:bg-pharma-orange/20'
  },
  indication: {
    icon: TrendingUp,
    label: 'Indication',
    className: 'bg-pharma-purple/10 text-pharma-purple border-pharma-purple/20 hover:bg-pharma-purple/20'
  }
};

export const EntityBadge = ({ type, size = 'md' }: EntityBadgeProps) => {
  const config = entityConfig[type];
  const Icon = config.icon;
  
  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-2.5 py-1.5',
    lg: 'text-base px-3 py-2'
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };

  return (
    <Badge 
      variant="outline" 
      className={`${config.className} ${sizeClasses[size]} inline-flex items-center gap-1.5 font-medium`}
    >
      <Icon className={iconSizes[size]} />
      {config.label}
    </Badge>
  );
};